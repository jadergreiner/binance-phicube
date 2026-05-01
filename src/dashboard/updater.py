"""Motor de fallback com polling adaptativo para o painel."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from src.dashboard.stream import PositionStream

logger = structlog.get_logger(__name__)

_FAST_POLL_INTERVAL_SECONDS = 2.0
_STABLE_POLL_INTERVAL_SECONDS = 10.0
_ADAPTIVE_WINDOW_SECONDS = 30.0
_STALE_WINDOW_SECONDS = 3.0
_MONITOR_INTERVAL_SECONDS = 0.5
_RATE_LIMIT_THRESHOLD = 1920
_RATE_LIMIT_PAUSE_SECONDS = 10.0
_USED_WEIGHT_HEADER = "x-mbx-used-weight"


class AdaptiveUpdater:
    """Observa o stream e ativa fallback REST quando a fonte primária degrada."""

    def __init__(
        self,
        *,
        now: Callable[[], datetime] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
        monitor_interval: float = _MONITOR_INTERVAL_SECONDS,
        fast_poll_interval: float = _FAST_POLL_INTERVAL_SECONDS,
        stable_poll_interval: float = _STABLE_POLL_INTERVAL_SECONDS,
        adaptive_window_seconds: float = _ADAPTIVE_WINDOW_SECONDS,
        stale_window_seconds: float = _STALE_WINDOW_SECONDS,
        rate_limit_threshold: int = _RATE_LIMIT_THRESHOLD,
        rate_limit_pause_seconds: float = _RATE_LIMIT_PAUSE_SECONDS,
    ) -> None:
        self._now = now or self._utcnow
        self._sleep = sleep or asyncio.sleep
        self._monitor_interval = monitor_interval
        self._fast_poll_interval = fast_poll_interval
        self._stable_poll_interval = stable_poll_interval
        self._adaptive_window_seconds = adaptive_window_seconds
        self._stale_window_seconds = stale_window_seconds
        self._rate_limit_threshold = rate_limit_threshold
        self._rate_limit_pause_seconds = rate_limit_pause_seconds

        self._stream: PositionStream | None = None
        self._monitor_task: asyncio.Task[None] | None = None
        self._polling_task: asyncio.Task[None] | None = None
        self._degraded_since: datetime | None = None
        self._last_update_at: datetime | None = None
        self._paused_until: datetime | None = None

    async def start(self, stream: PositionStream) -> None:
        """Inicia o monitoramento do stream e o fallback adaptativo."""
        if self._monitor_task is not None and not self._monitor_task.done():
            return

        self._stream = stream
        self._degraded_since = None
        self._paused_until = None
        self._refresh_last_update_at(stream)
        if self._last_update_at is None:
            self._last_update_at = self._now()

        self._monitor_task = asyncio.create_task(
            self._monitor_stream(),
            name="dashboard-adaptive-updater-monitor",
        )

    async def stop(self) -> None:
        """Cancela o monitoramento e qualquer polling em andamento."""
        monitor_task = self._monitor_task
        polling_task = self._polling_task

        self._monitor_task = None
        self._polling_task = None

        await self._cancel_task(monitor_task)
        await self._cancel_task(polling_task)

        self._stream = None
        self._degraded_since = None
        self._paused_until = None

    def _detect_stale(self, last_update: datetime, now: datetime) -> bool:
        return (now - last_update).total_seconds() > self._stale_window_seconds

    def _check_rate_limit(self, headers: Mapping[str, Any]) -> None:
        normalized_headers = {str(key).lower(): value for key, value in headers.items()}
        raw_used_weight = normalized_headers.get(_USED_WEIGHT_HEADER)
        if raw_used_weight is None:
            self._paused_until = None
            return

        try:
            used_weight = int(str(raw_used_weight))
        except (TypeError, ValueError):
            logger.warning(
                "dashboard_adaptive_updater_invalid_used_weight_header",
                value=raw_used_weight,
            )
            self._paused_until = None
            return

        if used_weight <= self._rate_limit_threshold:
            self._paused_until = None
            return

        now = self._now()
        self._paused_until = now + timedelta(seconds=self._rate_limit_pause_seconds)
        logger.warning(
            "dashboard_adaptive_updater_rate_limit_paused",
            used_weight=used_weight,
            threshold=self._rate_limit_threshold,
            resume_at=self._paused_until.isoformat(),
        )

    async def _monitor_stream(self) -> None:
        try:
            while True:
                stream = self._require_stream()
                self._refresh_last_update_at(stream)

                now = self._now()
                if self._last_update_at is not None:
                    if stream.get_status() == "online" and self._detect_stale(
                        self._last_update_at, now
                    ):
                        logger.warning(
                            "dashboard_adaptive_updater_stale_detected",
                            last_update_at=self._last_update_at.isoformat(),
                            stale_window_seconds=self._stale_window_seconds,
                        )
                        await stream._set_status("degraded")

                if stream.get_status() == "degraded":
                    if self._degraded_since is None:
                        self._degraded_since = now
                    if self._polling_task is None or self._polling_task.done():
                        self._polling_task = asyncio.create_task(
                            self._run_polling_loop(),
                            name="dashboard-adaptive-updater-polling",
                        )
                else:
                    self._degraded_since = None
                    self._paused_until = None
                    if self._polling_task is not None:
                        await self._cancel_task(self._polling_task)
                        self._polling_task = None

                await self._sleep(self._monitor_interval)
        except asyncio.CancelledError:
            raise

    async def _run_polling_loop(self) -> None:
        try:
            while True:
                stream = self._require_stream()
                if stream.get_status() != "degraded":
                    return

                await self._refresh_positions(stream)

                if stream.get_status() != "degraded":
                    return

                sleep_seconds = self._resolve_poll_sleep_seconds(self._now())
                await self._sleep(sleep_seconds)
        except asyncio.CancelledError:
            raise

    async def _refresh_positions(self, stream: PositionStream) -> None:
        exchange = stream._client._exchange
        current_positions = {position.symbol: position for position in stream.get_positions()}

        try:
            payload = await exchange.fapiPrivateV2GetPositionRisk()
            headers = getattr(exchange, "last_response_headers", {}) or {}
        except Exception as exc:
            logger.warning(
                "dashboard_adaptive_updater_poll_failed",
                error=str(exc),
            )
            return

        self._check_rate_limit(headers)

        updated_at = self._now()
        raw_positions = payload if isinstance(payload, list) else [payload]
        positions = {}

        for raw_position in raw_positions:
            position = stream._build_snapshot_position(raw_position, updated_at)
            if position is None:
                continue
            positions[position.symbol] = position

        self._log_reconciliation_inconsistency(current_positions, positions)
        stream._positions = positions
        stream._save_current_snapshot()
        self._last_update_at = updated_at

        logger.info(
            "dashboard_adaptive_updater_poll_succeeded",
            positions=len(positions),
            poll_interval_seconds=self._resolve_poll_interval(updated_at),
        )

        if stream.get_status() == "degraded":
            await self._restore_stream(stream)

    def _refresh_last_update_at(self, stream: PositionStream) -> None:
        latest_update = max(
            (position.updated_at for position in stream.get_positions()),
            default=None,
        )
        if latest_update is None:
            return

        if self._last_update_at is None or latest_update > self._last_update_at:
            self._last_update_at = latest_update

    def _resolve_poll_interval(self, now: datetime) -> float:
        if self._degraded_since is None:
            return self._fast_poll_interval

        degraded_for = (now - self._degraded_since).total_seconds()
        if degraded_for < self._adaptive_window_seconds:
            return self._fast_poll_interval
        return self._stable_poll_interval

    def _resolve_poll_sleep_seconds(self, now: datetime) -> float:
        interval = self._resolve_poll_interval(now)
        if self._paused_until is None or self._paused_until <= now:
            return interval

        pause_seconds = (self._paused_until - now).total_seconds()
        return max(interval, pause_seconds)

    def _require_stream(self) -> PositionStream:
        if self._stream is None:
            raise RuntimeError("AdaptiveUpdater não foi iniciado com um stream válido")
        return self._stream

    async def _restore_stream(self, stream: PositionStream) -> None:
        try:
            await stream.stop(status="degraded")
            await stream.start()
        except Exception as exc:
            logger.warning(
                "dashboard_adaptive_updater_stream_restore_failed",
                error=str(exc),
            )
            await stream._set_status("degraded")
            return

        if stream.get_status() != "online":
            logger.warning(
                "dashboard_adaptive_updater_stream_restore_incomplete",
                status=stream.get_status(),
            )
            return

        logger.info("dashboard_adaptive_updater_stream_restored")

    def _log_reconciliation_inconsistency(
        self,
        current_positions: Mapping[str, Any],
        refreshed_positions: Mapping[str, Any],
    ) -> None:
        inconsistent_symbols = sorted(
            symbol
            for symbol in set(current_positions) | set(refreshed_positions)
            if self._position_signature(current_positions.get(symbol))
            != self._position_signature(refreshed_positions.get(symbol))
        )
        if not inconsistent_symbols:
            return

        logger.warning(
            "dashboard_adaptive_updater_reconciliation_inconsistency_detected",
            symbols=inconsistent_symbols,
            local_positions=len(current_positions),
            binance_positions=len(refreshed_positions),
        )

    @staticmethod
    def _position_signature(position: Any) -> tuple[Any, ...] | None:
        if position is None:
            return None

        return (
            position.symbol,
            position.side,
            position.quantity,
            position.leverage,
            position.entry_price,
            position.mark_price,
            position.unrealized_pnl_usdt,
            position.margin_used_usdt,
            position.liquidation_price,
        )

    async def _cancel_task(self, task: asyncio.Task[None] | None) -> None:
        if task is None:
            return

        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(UTC)


__all__ = ["AdaptiveUpdater"]
