"""Testes unitários do updater adaptativo do painel."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.dashboard.models import PositionView
from src.dashboard.updater import AdaptiveUpdater


async def _wait_until(predicate: Any, *, timeout: float = 1.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("Condição esperada não foi satisfeita a tempo")


def _make_position(*, updated_at: datetime) -> PositionView:
    return PositionView(
        symbol="BTCUSDT",
        side="LONG",
        quantity=0.5,
        leverage=10,
        entry_price=95000.0,
        mark_price=96000.0,
        unrealized_pnl_usdt=250.0,
        margin_used_usdt=2400.0,
        liquidation_price=87000.0,
        updated_at=updated_at,
    )


def _make_snapshot_payload() -> list[dict[str, str]]:
    return [
        {
            "symbol": "BTCUSDT",
            "positionAmt": "0.5",
            "leverage": "10",
            "entryPrice": "95000",
            "markPrice": "96000",
            "unRealizedProfit": "250",
            "isolatedMargin": "2400",
            "liquidationPrice": "87000",
        }
    ]


class _TestClock:
    def __init__(self, current: datetime) -> None:
        self.current = current
        self.sleeps: list[float] = []
        self.after_sleep: Any = None

    def now(self) -> datetime:
        return self.current

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.current += timedelta(seconds=seconds)
        if self.after_sleep is not None:
            result = self.after_sleep(seconds)
            if asyncio.iscoroutine(result):
                await result
        await asyncio.sleep(0)


class _FakeExchange:
    def __init__(
        self,
        *,
        payload: list[dict[str, str]] | None = None,
        used_weights: list[int] | None = None,
    ) -> None:
        self._payload = payload or _make_snapshot_payload()
        self._used_weights = list(used_weights or [200])
        self.calls = 0
        self.last_response_headers: dict[str, str] = {}

    async def fapiPrivateV2GetPositionRisk(self) -> list[dict[str, str]]:
        index = min(self.calls, len(self._used_weights) - 1)
        self.last_response_headers = {
            "X-MBX-USED-WEIGHT": str(self._used_weights[index]),
        }
        self.calls += 1
        return self._payload


class _FakeStream:
    def __init__(
        self,
        *,
        status: str,
        positions: list[PositionView],
        exchange: _FakeExchange | None = None,
        fail_start: bool = False,
        transport_open: bool = True,
    ) -> None:
        self._status = status
        self._positions = {position.symbol: position for position in positions}
        self._exchange = exchange or _FakeExchange()
        self._client = SimpleNamespace(
            fetch_position_risk=self._fetch_position_risk,
            get_last_response_headers=self._get_last_response_headers,
        )
        self.fail_start = fail_start
        self.transport_open = transport_open
        self.status_events: list[str] = []
        self.saved_snapshots: list[list[PositionView]] = []
        self.start_calls = 0
        self.stop_calls = 0
        self.stop_statuses: list[str] = []

    def get_positions(self) -> list[PositionView]:
        return sorted(self._positions.values(), key=lambda position: position.symbol)

    def get_status(self) -> str:
        return self._status

    def has_non_recoverable_auth_failure(self) -> bool:
        return False

    def get_non_recoverable_auth_reason(self) -> str | None:
        return None

    def is_transport_open(self) -> bool:
        return self.transport_open

    async def _set_status(self, status: str) -> None:
        self._status = status
        self.status_events.append(status)

    async def start(self) -> bool:
        self.start_calls += 1
        if self.fail_start:
            await self._set_status("degraded")
            return False
        await self._set_status("online")
        return True

    async def stop(self, *, status: str = "offline") -> None:
        self.stop_calls += 1
        self.stop_statuses.append(status)
        if status != self._status:
            await self._set_status(status)

    async def _fetch_position_risk(self) -> list[dict[str, str]]:
        return await self._exchange.fapiPrivateV2GetPositionRisk()

    async def _notify_update(self) -> None:
        return None

    def _get_last_response_headers(self) -> dict[str, str]:
        return self._exchange.last_response_headers

    def _build_snapshot_position(
        self,
        raw_position: dict[str, str],
        updated_at: datetime,
    ) -> PositionView | None:
        quantity = float(raw_position.get("positionAmt", 0.0))
        if quantity == 0:
            return None

        return replace(
            next(iter(self._positions.values())),
            symbol=str(raw_position.get("symbol", "BTCUSDT")),
            side="LONG" if quantity > 0 else "SHORT",
            quantity=quantity,
            leverage=int(float(raw_position.get("leverage", 0))),
            entry_price=float(raw_position.get("entryPrice", 0.0)),
            mark_price=float(raw_position.get("markPrice", 0.0)),
            unrealized_pnl_usdt=float(raw_position.get("unRealizedProfit", 0.0)),
            margin_used_usdt=float(raw_position.get("isolatedMargin", 0.0)),
            liquidation_price=float(raw_position.get("liquidationPrice", 0.0)),
            updated_at=updated_at,
        )

    def _save_current_snapshot(self) -> None:
        self.saved_snapshots.append(self.get_positions())


@pytest.mark.asyncio
async def test_test_001_03_ausencia_de_update_marca_stream_como_degraded() -> None:
    base_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    clock = _TestClock(base_time)
    stale_position = _make_position(updated_at=base_time - timedelta(seconds=4))
    stream = _FakeStream(
        status="online",
        positions=[stale_position],
        fail_start=True,
        transport_open=False,
    )
    updater = AdaptiveUpdater(
        now=clock.now,
        sleep=clock.sleep,
        monitor_interval=0.01,
        stale_window_seconds=3.0,
    )

    try:
        await updater.start(stream)
        await _wait_until(lambda: "degraded" in stream.status_events)

        assert stream.status_events[0] == "degraded"
        assert stream.get_status() == "degraded"
    finally:
        await updater.stop()


@pytest.mark.asyncio
async def test_nao_marca_degraded_quando_stream_online_tem_transporte_aberto() -> None:
    base_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    clock = _TestClock(base_time)
    stale_position = _make_position(updated_at=base_time - timedelta(seconds=30))
    stream = _FakeStream(status="online", positions=[stale_position], fail_start=True)
    updater = AdaptiveUpdater(
        now=clock.now,
        sleep=clock.sleep,
        monitor_interval=0.01,
        stale_window_seconds=3.0,
    )

    try:
        await updater.start(stream)
        await asyncio.sleep(0.1)
        assert "degraded" not in stream.status_events
        assert stream.get_status() == "online"
    finally:
        await updater.stop()


@pytest.mark.asyncio
async def test_polling_inicia_em_2s_e_recua_para_10s_apos_30s() -> None:
    base_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    clock = _TestClock(base_time)
    stream = _FakeStream(
        status="degraded",
        positions=[_make_position(updated_at=base_time)],
        fail_start=True,
    )
    updater = AdaptiveUpdater(now=clock.now, sleep=clock.sleep, monitor_interval=0.5)

    await updater.start(stream)
    await _wait_until(lambda: 10.0 in clock.sleeps)

    assert 2.0 in clock.sleeps
    assert 10.0 in clock.sleeps
    assert stream._exchange.calls >= 2

    await updater.stop()


@pytest.mark.asyncio
async def test_rate_limit_acima_do_limite_pausa_polling() -> None:
    base_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    clock = _TestClock(base_time)
    exchange = _FakeExchange(used_weights=[1930])
    stream = _FakeStream(
        status="degraded",
        positions=[_make_position(updated_at=base_time)],
        exchange=exchange,
        fail_start=True,
    )
    updater = AdaptiveUpdater(now=clock.now, sleep=clock.sleep, monitor_interval=0.5)

    await updater.start(stream)
    await _wait_until(lambda: any(seconds >= 10.0 for seconds in clock.sleeps))

    assert exchange.calls >= 1
    assert any(seconds >= 10.0 for seconds in clock.sleeps)

    await updater.stop()


@pytest.mark.asyncio
async def test_reconciliacao_sobrescreve_cache_local_e_restaura_stream() -> None:
    base_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    stream = _FakeStream(
        status="degraded",
        positions=[_make_position(updated_at=base_time)],
        exchange=_FakeExchange(
            payload=[
                {
                    "symbol": "BTCUSDT",
                    "positionAmt": "1.25",
                    "leverage": "12",
                    "entryPrice": "97000",
                    "markPrice": "97200",
                    "unRealizedProfit": "150",
                    "isolatedMargin": "3000",
                    "liquidationPrice": "89000",
                }
            ]
        ),
    )
    warning_mock = MagicMock()
    updater = AdaptiveUpdater(monitor_interval=0.01)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.dashboard.updater.logger.warning", warning_mock)
        await updater.start(stream)
        await _wait_until(lambda: stream.get_status() == "online")

    position = stream.get_positions()[0]
    assert position.quantity == pytest.approx(1.25)
    assert position.leverage == 12
    assert stream.stop_calls == 1
    assert stream.start_calls == 1
    assert stream.stop_statuses == ["degraded"]
    assert stream.saved_snapshots[-1][0].quantity == pytest.approx(1.25)
    assert any(
        call.args[0] == "dashboard_adaptive_updater_reconciliation_inconsistency_detected"
        for call in warning_mock.call_args_list
    )

    await updater.stop()
