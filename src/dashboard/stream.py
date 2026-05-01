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
from src.dashboard.client import DashboardClient
from src.dashboard.models import ConnectionStatus, PositionView
from src.monitoring.logger import get_logger

logger = get_logger(__name__)

_FUTURES_STREAM_MAINNET_URL = "wss://fstream.binance.com/ws"
_FUTURES_STREAM_TESTNET_URL = "wss://stream.binancefuture.com/ws"
_STREAM_HEARTBEAT_SECONDS = 30
_DEFAULT_KEEPALIVE_INTERVAL_SECONDS = 30 * 60

StatusChangeCallback = Callable[[ConnectionStatus], Awaitable[None] | None]


class PositionStream:
    """Mantém em memória o snapshot de posições e aplica updates incrementais."""

    def __init__(
        self,
        client: DashboardClient,
        *,
        cache: DashboardCache | None = None,
        on_status_change: StatusChangeCallback | None = None,
        session_factory: Callable[[], aiohttp.ClientSession] | None = None,
        keepalive_interval: float = _DEFAULT_KEEPALIVE_INTERVAL_SECONDS,
    ) -> None:
        self._client = client
        self._cache = cache
        self.on_status_change = on_status_change
        self._session_factory = session_factory or aiohttp.ClientSession
        self._keepalive_interval = keepalive_interval

        self._positions: dict[str, PositionView] = {}
        self._status: ConnectionStatus = "offline"
        self._listen_key: str | None = None
        self._session: aiohttp.ClientSession | None = None
        self._websocket: aiohttp.ClientWebSocketResponse | None = None
        self._stream_task: asyncio.Task[None] | None = None
        self._keepalive_task: asyncio.Task[None] | None = None

        self.degraded_event = asyncio.Event()

    async def start(self) -> None:
        """Carrega o snapshot inicial e inicia o userData stream."""
        if self._stream_task is not None and not self._stream_task.done():
            return

        await self._load_initial_snapshot()

        try:
            self._listen_key = await self._create_listen_key()
            session = self._session_factory()
            self._session = session
            self._websocket = await session.ws_connect(
                self._build_stream_url(self._listen_key),
                heartbeat=_STREAM_HEARTBEAT_SECONDS,
            )
        except Exception as exc:
            logger.exception("dashboard_position_stream_connect_failed", error=str(exc))
            await self._close_session()
            await self._set_status("degraded")
            return

        self._stream_task = asyncio.create_task(
            self._consume_stream(),
            name="dashboard-position-stream",
        )
        self._keepalive_task = asyncio.create_task(
            self._keepalive_listen_key(),
            name="dashboard-position-stream-keepalive",
        )
        if self._status != "cached":
            await self._set_status("online")
        logger.info(
            "dashboard_position_stream_started",
            positions=len(self._positions),
            testnet=self._is_testnet(),
        )

    async def stop(self, *, status: ConnectionStatus = "offline") -> None:
        """Encerra o stream e libera recursos associados."""
        for task in (self._stream_task, self._keepalive_task):
            if task is not None:
                task.cancel()

        tasks_to_wait = [
            task for task in (self._stream_task, self._keepalive_task) if task is not None
        ]
        if tasks_to_wait:
            await asyncio.gather(*tasks_to_wait, return_exceptions=True)

        self._stream_task = None
        self._keepalive_task = None

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

    async def _load_initial_snapshot(self) -> None:
        try:
            payload = await self._client._exchange.fapiPrivateV2GetPositionRisk()
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
        logger.info("dashboard_position_snapshot_loaded", positions=len(self._positions))

    async def _create_listen_key(self) -> str:
        payload = await self._client._exchange.fapiPrivatePostListenKey()
        listen_key = payload.get("listenKey")

        if not listen_key:
            raise ValueError("Binance não retornou listenKey válido para o painel")

        return str(listen_key)

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

            if current_position is not None and updated_at <= current_position.updated_at:
                updated_at = current_position.updated_at + timedelta(microseconds=1)

            if current_position is None:
                self._positions[symbol] = PositionView(
                    symbol=symbol,
                    side=self._resolve_side(quantity),
                    quantity=quantity,
                    leverage=0,
                    entry_price=self._to_float(raw_update.get("ep")),
                    mark_price=0.0,
                    unrealized_pnl_usdt=self._to_float(raw_update.get("up")),
                    margin_used_usdt=self._resolve_stream_margin(raw_update),
                    liquidation_price=None,
                    updated_at=updated_at,
                )
                continue

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
            payload = await self._client._exchange.fapiPrivateV2GetPositionRisk({"symbol": symbol})
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
                await self._client._exchange.fapiPrivatePutListenKey(
                    {"listenKey": self._listen_key}
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("dashboard_position_stream_keepalive_failed", error=str(exc))
            if self._websocket is not None and not self._websocket.closed:
                await self._websocket.close()
            await self._delete_listen_key()
            self._listen_key = None
            await self._close_session()
            await self._set_status("degraded")

    async def _delete_listen_key(self) -> None:
        if self._listen_key is None:
            return

        delete_listen_key = getattr(self._client._exchange, "fapiPrivateDeleteListenKey", None)
        if delete_listen_key is None:
            return

        try:
            await delete_listen_key({"listenKey": self._listen_key})
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

    def _save_current_snapshot(self) -> None:
        if self._cache is None or not self._positions:
            return

        self._cache.save_snapshot(self.get_positions())

    def _build_snapshot_position(
        self,
        raw_position: dict[str, Any],
        updated_at: datetime,
    ) -> PositionView | None:
        quantity = self._to_float(raw_position.get("positionAmt"))
        if quantity == 0:
            return None

        leverage = int(self._to_float(raw_position.get("leverage")))
        return PositionView(
            symbol=str(raw_position.get("symbol", "")),
            side=self._resolve_side(quantity),
            quantity=quantity,
            leverage=leverage,
            entry_price=self._to_float(raw_position.get("entryPrice")),
            mark_price=self._to_float(raw_position.get("markPrice")),
            unrealized_pnl_usdt=self._to_float(raw_position.get("unRealizedProfit")),
            margin_used_usdt=self._resolve_snapshot_margin(raw_position, leverage, quantity),
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


__all__ = ["PositionStream", "StatusChangeCallback"]
