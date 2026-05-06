"""Stream assíncrono de posições do painel via userData da Binance Futures."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from aiohttp import WSMsgType

from src.dashboard.cache import DashboardCache
from src.dashboard.client import DashboardAuthError, DashboardClient
from src.dashboard.models import ConnectionStatus, PositionView
from src.monitoring.logger import get_logger

logger = get_logger(__name__)

_FUTURES_STREAM_MAINNET_URL = "wss://fstream.binance.com/ws"
_FUTURES_STREAM_TESTNET_URL = "wss://stream.binancefuture.com/ws"
_STREAM_HEARTBEAT_SECONDS = 30
_DEFAULT_KEEPALIVE_INTERVAL_SECONDS = 30 * 60
_HEALTH_CHECK_INTERVAL_SECONDS = 10
_HEALTH_CHECK_TIMEOUT_SECONDS = 45
_INITIAL_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 60.0
_MAX_RECONNECT_ATTEMPTS = 10

StatusChangeCallback = Callable[[ConnectionStatus], Awaitable[None] | None]
UpdateCallback = Callable[["PositionStream"], Awaitable[None] | None]


def _default_session_factory() -> aiohttp.ClientSession:
    # Usa resolvedor por thread para evitar falhas intermitentes do AsyncResolver/aiodns.
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    return aiohttp.ClientSession(connector=connector)


class PositionStream:
    """Mantém em memória o snapshot de posições e aplica updates incrementais."""

    def __init__(
        self,
        client: DashboardClient,
        *,
        cache: DashboardCache | None = None,
        on_status_change: StatusChangeCallback | None = None,
        on_update: UpdateCallback | None = None,
        session_factory: Callable[[], aiohttp.ClientSession] | None = None,
        keepalive_interval: float = _DEFAULT_KEEPALIVE_INTERVAL_SECONDS,
    ) -> None:
        self._client = client
        self._cache = cache
        self.on_status_change = on_status_change
        self.on_update = on_update
        self._session_factory = session_factory or _default_session_factory
        self._keepalive_interval = keepalive_interval

        self._positions: dict[str, PositionView] = {}
        self._status: ConnectionStatus = "offline"
        self._listen_key: str | None = None
        self._session: aiohttp.ClientSession | None = None
        self._websocket: aiohttp.ClientWebSocketResponse | None = None
        self._stream_task: asyncio.Task[None] | None = None
        self._keepalive_task: asyncio.Task[None] | None = None
        self._health_check_task: asyncio.Task[None] | None = None

        self.degraded_event = asyncio.Event()
        self._last_update_at: datetime | None = None
        self._reconnect_backoff_seconds = _INITIAL_BACKOFF_SECONDS
        self._reconnect_attempts = 0
        self._non_recoverable_auth_failure = False
        self._non_recoverable_auth_reason: str | None = None
        self._leverage_unresolved_symbols_logged: set[str] = set()

    async def start(self) -> bool:
        """Carrega o snapshot inicial e inicia o userData stream."""
        if self._stream_task is not None and not self._stream_task.done():
            return True

        await self._load_initial_snapshot()

        try:
            self._listen_key = await self._create_listen_key()
            session = self._session_factory()
            self._session = session
            self._websocket = await session.ws_connect(
                self._build_stream_url(self._listen_key),
                heartbeat=_STREAM_HEARTBEAT_SECONDS,
            )
            self._non_recoverable_auth_failure = False
            self._non_recoverable_auth_reason = None
        except DashboardAuthError as exc:
            self._non_recoverable_auth_failure = True
            self._non_recoverable_auth_reason = exc.issue.reason
            logger.error(
                "dashboard_position_stream_non_recoverable_auth_failure",
                reason=exc.issue.reason,
                action_required=exc.issue.detail,
                testnet=self._is_testnet(),
            )
            await self._close_session()
            await self._set_status("offline")
            raise
        except Exception as exc:
            logger.exception("dashboard_position_stream_connect_failed", error=str(exc))
            await self._close_session()
            await self._set_status("degraded")
            return False

        self._stream_task = asyncio.create_task(
            self._consume_stream(),
            name="dashboard-position-stream",
        )
        self._keepalive_task = asyncio.create_task(
            self._keepalive_listen_key(),
            name="dashboard-position-stream-keepalive",
        )
        self._health_check_task = asyncio.create_task(
            self._health_check_loop(),
            name="dashboard-position-stream-health-check",
        )
        if self._status != "cached":
            await self._set_status("online")
        self._reconnect_attempts = 0
        logger.info(
            "dashboard_position_stream_started",
            positions=len(self._positions),
            testnet=self._is_testnet(),
        )
        return True

    async def stop(self, *, status: ConnectionStatus = "offline") -> None:
        """Encerra o stream e libera recursos associados."""
        for task in (self._stream_task, self._keepalive_task, self._health_check_task):
            if task is not None:
                task.cancel()

        tasks_to_wait = [
            task for task in (self._stream_task, self._keepalive_task, self._health_check_task)
            if task is not None
        ]
        if tasks_to_wait:
            await asyncio.gather(*tasks_to_wait, return_exceptions=True)

        self._stream_task = None
        self._keepalive_task = None
        self._health_check_task = None

        if self._websocket is not None and not self._websocket.closed:
            await self._websocket.close()
        self._websocket = None

        await self._delete_listen_key()
        self._listen_key = None

        await self._close_session()
        await self._set_status(status)
        logger.info("dashboard_position_stream_stopped")

    def get_positions(self) -> list[PositionView]:
        """Retorna o estado atual das posições abertas em memória."""
        return sorted(self._positions.values(), key=lambda position: position.symbol)

    def get_status(self) -> ConnectionStatus:
        """Retorna o status atual do stream do painel."""
        return self._status

    def has_non_recoverable_auth_failure(self) -> bool:
        return self._non_recoverable_auth_failure

    def get_non_recoverable_auth_reason(self) -> str | None:
        return self._non_recoverable_auth_reason

    async def _load_initial_snapshot(self) -> None:
        try:
            payload = await self._client.fetch_position_risk()
        except Exception as exc:
            logger.warning("dashboard_position_snapshot_load_failed", error=str(exc))
            if self._cache is None:
                raise

            cached_positions = await self._cache.load_snapshot()
            if cached_positions is None:
                raise

            self._positions = {position.symbol: position for position in cached_positions}
            await self._set_status("cached")
            logger.info(
                "dashboard_position_snapshot_cache_loaded",
                positions=len(self._positions),
            )
            return

        updated_at = datetime.now(UTC)
        positions: dict[str, PositionView] = {}
        for raw_position in payload:
            position = self._build_snapshot_position(raw_position, updated_at)
            if position is None:
                continue
            positions[position.symbol] = position

        self._positions = positions
        self._save_current_snapshot()
        await self._notify_update()
        logger.info("dashboard_position_snapshot_loaded", positions=len(self._positions))

    async def _create_listen_key(self) -> str:
        return await self._client.create_listen_key()

    async def _consume_stream(self) -> None:
        if self._websocket is None:
            return

        try:
            while True:
                message = await self._websocket.receive()

                if message.type == WSMsgType.TEXT:
                    payload = json.loads(message.data)
                    await self._handle_stream_payload(payload)
                    continue

                if message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING}:
                    raise ConnectionError("userData stream encerrado pela Binance")

                if message.type == WSMsgType.ERROR:
                    raise ConnectionError("userData stream retornou erro")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("dashboard_position_stream_loop_failed", error=str(exc))
            await self._set_status("degraded")

    async def _handle_stream_payload(self, payload: dict[str, Any]) -> None:
        if payload.get("e") != "ACCOUNT_UPDATE":
            return

        await self._apply_account_update(payload)
        self._last_update_at = datetime.now(UTC)
        await self._notify_update()
        await self._set_status("online")

    async def _apply_account_update(self, payload: dict[str, Any]) -> None:
        account_update = payload.get("a", {})
        position_updates = account_update.get("P", [])
        updated_at = datetime.now(UTC)

        for raw_update in position_updates:
            symbol = str(raw_update.get("s", "")).strip()
            if not symbol:
                continue

            quantity = self._to_float(raw_update.get("pa"))
            if quantity == 0:
                self._positions.pop(symbol, None)
                continue

            current_position = self._positions.get(symbol)
            if current_position is None:
                current_position = await self._fetch_position_snapshot(symbol, updated_at)

            if current_position is None:
                logger.warning(
                    "dashboard_position_update_without_snapshot",
                    symbol=symbol,
                )
                continue

            if updated_at <= current_position.updated_at:
                updated_at = current_position.updated_at + timedelta(microseconds=1)

            self._positions[symbol] = replace(
                current_position,
                side=self._resolve_side(quantity),
                quantity=quantity,
                entry_price=self._maybe_float(raw_update.get("ep"), current_position.entry_price),
                unrealized_pnl_usdt=self._maybe_float(
                    raw_update.get("up"), current_position.unrealized_pnl_usdt
                ),
                margin_used_usdt=self._maybe_float(
                    raw_update.get("iw"), current_position.margin_used_usdt
                ),
                updated_at=updated_at,
            )

        self._save_current_snapshot()

    async def _fetch_position_snapshot(
        self,
        symbol: str,
        updated_at: datetime,
    ) -> PositionView | None:
        try:
            payload = await self._client.fetch_position_risk(symbol=symbol)
        except Exception as exc:
            logger.warning(
                "dashboard_position_snapshot_refresh_failed",
                symbol=symbol,
                error=str(exc),
            )
            return None

        raw_positions = payload if isinstance(payload, list) else [payload]
        for raw_position in raw_positions:
            if raw_position.get("symbol") != symbol:
                continue
            return self._build_snapshot_position(raw_position, updated_at)

        return None

    async def _keepalive_listen_key(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._keepalive_interval)
                if self._listen_key is None:
                    return
                try:
                    await self._client.renew_listen_key(self._listen_key)
                    logger.debug(
                        "dashboard_position_stream_keepalive_success",
                        listen_key=self._listen_key[:8] + "...",
                    )
                except Exception as renew_exc:
                    logger.warning(
                        "dashboard_position_stream_keepalive_renew_failed",
                        error=str(renew_exc),
                    )
                    raise
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception(
                "dashboard_position_stream_keepalive_failed",
                error=str(exc),
                reconnect_attempts=self._reconnect_attempts,
            )
            if self._websocket is not None and not self._websocket.closed:
                await self._websocket.close()
            await self._delete_listen_key()
            self._listen_key = None
            await self._close_session()
            await self._set_status("degraded")

    async def _delete_listen_key(self) -> None:
        if self._listen_key is None:
            return

        try:
            await self._client.delete_listen_key(self._listen_key)
        except Exception as exc:
            logger.warning("dashboard_position_stream_delete_listen_key_failed", error=str(exc))

    async def _close_session(self) -> None:
        if self._session is None:
            return

        if not self._session.closed:
            await self._session.close()
        self._session = None

    async def _set_status(self, status: ConnectionStatus) -> None:
        if status == self._status:
            return

        self._status = status
        if status == "degraded":
            self.degraded_event.set()
        else:
            self.degraded_event.clear()

        if self.on_status_change is None:
            return

        try:
            callback_result = self.on_status_change(status)
            if inspect.isawaitable(callback_result):
                await callback_result
        except Exception as exc:
            logger.warning(
                "dashboard_position_stream_status_callback_failed",
                status=status,
                error=str(exc),
            )

    async def _notify_update(self) -> None:
        if self.on_update is None:
            return

        try:
            callback_result = self.on_update(self)
            if inspect.isawaitable(callback_result):
                await callback_result
        except Exception as exc:
            logger.warning("dashboard_position_stream_update_callback_failed", error=str(exc))

    def _save_current_snapshot(self) -> None:
        if self._cache is None or not self._positions:
            return

        self._cache.save_snapshot(self.get_positions())

    async def _health_check_loop(self) -> None:
        """Monitora a saúde do stream e tenta recovery se degradado."""
        try:
            while True:
                await asyncio.sleep(_HEALTH_CHECK_INTERVAL_SECONDS)

                if self._status == "offline":
                    continue

                if self._status == "online":
                    await self._check_stream_freshness()
                    continue

                if self._status == "degraded":
                    await self._attempt_recovery()
                    continue

                if self._status == "cached":
                    await self._check_stream_freshness()
                    continue
        except asyncio.CancelledError:
            raise

    async def _check_stream_freshness(self) -> None:
        """Verifica se há updates recentes; marca degraded se muito antigo."""
        if self._last_update_at is None:
            return

        time_since_update = (datetime.now(UTC) - self._last_update_at).total_seconds()
        if time_since_update > _HEALTH_CHECK_TIMEOUT_SECONDS:
            logger.warning(
                "dashboard_position_stream_stale_data",
                seconds_since_update=time_since_update,
                threshold=_HEALTH_CHECK_TIMEOUT_SECONDS,
            )
            await self._set_status("degraded")

    async def _attempt_recovery(self) -> None:
        """Tenta reconectar após degradado."""
        self._reconnect_attempts += 1

        if self._reconnect_attempts > _MAX_RECONNECT_ATTEMPTS:
            logger.error(
                "dashboard_position_stream_max_reconnect_attempts_exceeded",
                max_attempts=_MAX_RECONNECT_ATTEMPTS,
            )
            return
        if self._non_recoverable_auth_failure:
            logger.error(
                "dashboard_position_stream_reconnect_blocked_non_recoverable_auth",
                reason=self._non_recoverable_auth_reason,
            )
            await self._set_status("offline")
            return

        backoff = self._calculate_backoff()
        logger.info(
            "dashboard_position_stream_reconnect_attempt",
            attempt=self._reconnect_attempts,
            backoff_seconds=backoff,
            max_attempts=_MAX_RECONNECT_ATTEMPTS,
        )

        await asyncio.sleep(backoff)

        try:
            started = await self.start()
            if not started:
                logger.warning(
                    "dashboard_position_stream_reconnect_incomplete",
                    attempt=self._reconnect_attempts,
                    status=self.get_status(),
                )
        except Exception as exc:
            logger.warning(
                "dashboard_position_stream_reconnect_failed",
                attempt=self._reconnect_attempts,
                error=str(exc),
            )

    def _calculate_backoff(self) -> float:
        """Calcula backoff exponencial com jitter."""
        import random

        backoff = self._reconnect_backoff_seconds * (2 ** (self._reconnect_attempts - 1))
        backoff = min(backoff, _MAX_BACKOFF_SECONDS)
        jitter = random.uniform(0, backoff * 0.1)
        return backoff + jitter

    def _build_snapshot_position(
        self,
        raw_position: dict[str, Any],
        updated_at: datetime,
    ) -> PositionView | None:
        quantity = self._to_float(raw_position.get("positionAmt"))
        if quantity == 0:
            return None

        symbol = str(raw_position.get("symbol", ""))
        leverage = int(self._to_float(raw_position.get("leverage")))
        margin_used_usdt = self._resolve_snapshot_margin(raw_position, leverage, quantity)
        if leverage <= 0:
            inferred_leverage, source = self._infer_leverage(raw_position, quantity=quantity)
            if inferred_leverage > 0:
                logger.info(
                    "dashboard_position_leverage_inferred",
                    symbol=symbol,
                    source=source,
                    raw_leverage=raw_position.get("leverage"),
                    inferred_leverage=inferred_leverage,
                    notional=raw_position.get("notional"),
                    position_initial_margin=raw_position.get("positionInitialMargin"),
                )
                leverage = inferred_leverage
                self._leverage_unresolved_symbols_logged.discard(symbol)
            elif symbol not in self._leverage_unresolved_symbols_logged:
                logger.warning(
                    "dashboard_position_leverage_unresolved",
                    symbol=symbol,
                    source="unresolved",
                    raw_leverage=raw_position.get("leverage"),
                    notional=raw_position.get("notional"),
                    position_initial_margin=raw_position.get("positionInitialMargin"),
                    mark_price=raw_position.get("markPrice"),
                    quantity=quantity,
                )
                self._leverage_unresolved_symbols_logged.add(symbol)

        return PositionView(
            symbol=symbol,
            side=self._resolve_side(quantity),
            quantity=quantity,
            leverage=leverage,
            entry_price=self._to_float(raw_position.get("entryPrice")),
            mark_price=self._to_float(raw_position.get("markPrice")),
            unrealized_pnl_usdt=self._to_float(raw_position.get("unRealizedProfit")),
            margin_used_usdt=margin_used_usdt,
            liquidation_price=self._maybe_liquidation_price(raw_position.get("liquidationPrice")),
            updated_at=updated_at,
        )

    def _resolve_snapshot_margin(
        self,
        raw_position: dict[str, Any],
        leverage: int,
        quantity: float,
    ) -> float:
        explicit_margin = self._first_non_empty(
            raw_position.get("positionInitialMargin"),
            raw_position.get("isolatedMargin"),
        )
        if explicit_margin is not None:
            return self._to_float(explicit_margin)

        notional = abs(self._to_float(raw_position.get("notional")))
        if leverage > 0:
            return notional / leverage

        return abs(quantity) * self._to_float(raw_position.get("markPrice"))

    def _infer_leverage(self, raw_position: dict[str, Any], *, quantity: float) -> tuple[int, str]:
        explicit_margin = self._first_non_empty(
            raw_position.get("positionInitialMargin"),
            raw_position.get("isolatedMargin"),
        )
        if explicit_margin is None:
            return 0, "unresolved"

        explicit_margin_value = self._to_float(explicit_margin)
        if explicit_margin_value <= 0:
            return 0, "unresolved"

        notional = abs(self._to_float(raw_position.get("notional")))
        if notional > 0:
            leverage = int(round(notional / explicit_margin_value))
            if leverage > 0:
                return leverage, "inferred_notional_margin"

        mark_price = self._to_float(raw_position.get("markPrice"))
        fallback_notional = abs(quantity) * mark_price
        if fallback_notional > 0:
            leverage = int(round(fallback_notional / explicit_margin_value))
            if leverage > 0:
                return leverage, "inferred_qty_mark_margin"
        return 0, "unresolved"

    def _resolve_stream_margin(self, raw_update: dict[str, Any]) -> float:
        return self._to_float(self._first_non_empty(raw_update.get("iw"), raw_update.get("im")))

    def _build_stream_url(self, listen_key: str) -> str:
        base_url = (
            _FUTURES_STREAM_TESTNET_URL if self._is_testnet() else _FUTURES_STREAM_MAINNET_URL
        )
        return f"{base_url}/{listen_key}"

    def _is_testnet(self) -> bool:
        return bool(getattr(self._client._settings, "binance_testnet", False))

    @staticmethod
    def _resolve_side(quantity: float) -> str:
        return "LONG" if quantity > 0 else "SHORT"

    @staticmethod
    def _to_float(value: Any) -> float:
        if value in (None, ""):
            return 0.0
        return float(value)

    @classmethod
    def _maybe_float(cls, value: Any, default: float) -> float:
        if value in (None, ""):
            return default
        return cls._to_float(value)

    @classmethod
    def _maybe_liquidation_price(cls, value: Any) -> float | None:
        liquidation_price = cls._to_float(value)
        return None if liquidation_price == 0 else liquidation_price

    @staticmethod
    def _first_non_empty(*values: Any) -> Any:
        for value in values:
            if value not in (None, ""):
                return value
        return None


__all__ = ["PositionStream", "StatusChangeCallback", "UpdateCallback"]
