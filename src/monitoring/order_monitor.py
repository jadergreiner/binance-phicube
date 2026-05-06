"""
Monitor de ordens e posições abertas — detecta encerramento de trades.

Verifica periodicamente o estado das ordens SL/TP e posições registradas no
MongoDB, detectando quatro cenários operacionais:

    1. TP executado  → fetch_order → CLOSED_TP com PnL real
    2. SL executado  → fetch_order → CLOSED_SL com PnL real
    3. SL cancelado  → notificação Telegram CRITICAL ao operador
    4. Fechamento manual → cancelar ordens remanescentes → CLOSED_MANUAL

Decisão de design (DD-002): SEM recolocação automática de SL — o operador
decide se e quando recolocar a proteção.

Ciclo: 60 segundos (configurável via parâmetro `interval_seconds`).
Padrão de loop: igual ao PerformanceReporter (SPEC_008).
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import ccxt.async_support as ccxt

from src.exchange.binance_client import BinanceClient
from src.monitoring.logger import get_logger
from src.notifications.events import NotificationEvent, SLMissingEvent
from src.notifications.notifier import Notifier
from src.storage.repository import MongoRepository
from src.trading.order_manager import TradeStatus

logger = get_logger(__name__)

# Erros fatais que não entram em retry (padrão SPEC_007)
_FATAL_ERRORS = (
    ccxt.AuthenticationError,
    ccxt.InsufficientFunds,
    ccxt.BadSymbol,
    ccxt.InvalidOrder,
)


class OrderMonitor:
    """Monitora ordens e posições abertas em loop periódico.

    Detecta encerramento de trades (TP/SL executados, fechamento manual)
    e SL cancelado sem posição protegida, atualizando o MongoDB e notificando
    o operador conforme necessário.
    """

    def __init__(
        self,
        client: BinanceClient,
        repository: MongoRepository,
        notifier: Notifier,
        interval_seconds: int = 60,
    ) -> None:
        self._client = client
        self._repository = repository
        self._notifier = notifier
        self._interval_seconds = interval_seconds
        # Guard de notificação duplicada: evita spam de alertas de SL ausente.
        # Persistido apenas em memória — em restart, pode gerar um segundo alerta
        # (comportamento aceitável por DD-003).
        self._notified_sl_missing: set[str] = set()

    async def run(self) -> None:
        """Loop infinito com intervalo configurável.

        Encerra graciosamente ao receber CancelledError.
        """
        logger.info("order_monitor_started", interval_seconds=self._interval_seconds)

        while True:
            try:
                await self._check_all_open_trades()
            except asyncio.CancelledError:
                logger.info("order_monitor_stopped")
                return
            except Exception as exc:
                logger.error(
                    "order_monitor_cycle_error",
                    error_type=type(exc).__name__,
                )

            try:
                await asyncio.sleep(self._interval_seconds)
            except asyncio.CancelledError:
                logger.info("order_monitor_stopped")
                return

    async def _check_all_open_trades(self) -> None:
        """Busca todos os trades OPEN no MongoDB e verifica cada um."""
        trades = await self._repository.get_open_trades()
        if not trades:
            logger.debug("order_monitor_no_open_trades")
            return

        logger.debug("order_monitor_checking_trades", count=len(trades))

        for trade in trades:
            try:
                await self._check_trade(trade)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # RF-007: falha em um símbolo não afeta os outros
                logger.error(
                    "order_monitor_trade_check_error",
                    symbol=trade.get("symbol"),
                    entry_order_id=trade.get("entry_order_id"),
                    error_type=type(exc).__name__,
                )

    async def _check_trade(self, trade: dict) -> None:
        """Verifica o estado de um único trade na exchange.

        Fluxo de verificação:
            1. Verificar SL: cancelado → alerta; executado → CLOSED_SL
            2. Verificar TP: executado → CLOSED_TP
            3. Se position = 0 e ordens ainda abertas → fechamento manual
        """
        symbol = trade.get("symbol", "")
        sl_order_id = trade.get("sl_order_id")
        tp_order_id = trade.get("tp_order_id")

        # ─── Verifica SL ─────────────────────────────────────────────────────
        if sl_order_id:
            sl_order = await self._fetch_order_with_retry(sl_order_id, symbol)

            if sl_order is not None:
                sl_status = sl_order.get("status", "")

                if sl_status == "closed":
                    # SL executado — registrar fechamento com PnL real
                    await self._handle_sl_executed(trade, sl_order)
                    return

                if sl_status in ("canceled", "cancelled", "expired"):
                    # SL cancelado — verificar se posição ainda existe
                    current_price = await self._get_current_price(symbol)
                    if current_price is not None:
                        position_open = await self._is_position_open(symbol)
                        if position_open:
                            await self._handle_sl_missing(trade, current_price)
                    # Se posição não existe mais, não alerta — já encerrada
                    return

        # ─── Verifica TP ─────────────────────────────────────────────────────
        if tp_order_id:
            tp_order = await self._fetch_order_with_retry(tp_order_id, symbol)

            if tp_order is not None:
                tp_status = tp_order.get("status", "")

                if tp_status == "closed":
                    # TP executado — registrar fechamento com PnL real
                    await self._handle_tp_executed(trade, tp_order)
                    return

        # ─── Verifica fechamento manual ───────────────────────────────────────
        position_open = await self._is_position_open(symbol)
        if not position_open:
            # Posição = 0, mas trade ainda OPEN no MongoDB → fechamento manual
            await self._handle_manual_close(trade)

    async def _handle_tp_executed(self, trade: dict, order: dict) -> None:
        """Registra encerramento por TP com exit_price real."""
        symbol = trade.get("symbol", "")
        entry_order_id = trade.get("entry_order_id", "")

        # Campo `average` reflete o preço médio de execução real (DD-004)
        exit_price = float(order.get("average") or order.get("price") or 0.0)
        pnl_usdt = self._calc_pnl(trade, exit_price)

        await self._repository.update_trade_status(
            entry_order_id=entry_order_id,
            status=TradeStatus.CLOSED_TP,
            exit_price=exit_price,
            pnl_usdt=pnl_usdt,
            close_reason="tp_executed",
        )

        await self._repository.audit(
            "trade_closed_tp",
            {
                "entry_order_id": entry_order_id,
                "symbol": symbol,
                "exit_price": exit_price,
                "pnl_usdt": pnl_usdt,
            },
        )

        logger.info(
            "trade_closed_tp",
            symbol=symbol,
            entry_order_id=entry_order_id,
            exit_price=exit_price,
            pnl_usdt=pnl_usdt,
        )

    async def _handle_sl_executed(self, trade: dict, order: dict) -> None:
        """Registra encerramento por SL com exit_price real."""
        symbol = trade.get("symbol", "")
        entry_order_id = trade.get("entry_order_id", "")

        # Campo `average` reflete slippage real — não usar stopPrice (DD-004)
        exit_price = float(order.get("average") or order.get("price") or 0.0)
        pnl_usdt = self._calc_pnl(trade, exit_price)

        await self._repository.update_trade_status(
            entry_order_id=entry_order_id,
            status=TradeStatus.CLOSED_SL,
            exit_price=exit_price,
            pnl_usdt=pnl_usdt,
            close_reason="sl_executed",
        )

        await self._repository.audit(
            "trade_closed_sl",
            {
                "entry_order_id": entry_order_id,
                "symbol": symbol,
                "exit_price": exit_price,
                "pnl_usdt": pnl_usdt,
            },
        )

        logger.info(
            "trade_closed_sl",
            symbol=symbol,
            entry_order_id=entry_order_id,
            exit_price=exit_price,
            pnl_usdt=pnl_usdt,
        )

    async def _handle_sl_missing(self, trade: dict, current_price: float) -> None:
        """Notifica operador de SL cancelado ou ausente (RF-001, RF-005).

        Guard de duplicata: notifica apenas na primeira detecção por trade_id.
        """
        entry_order_id = trade.get("entry_order_id", "")

        # RF-005: guard de notificação duplicada (set em memória)
        if entry_order_id in self._notified_sl_missing:
            logger.debug("sl_missing_already_notified", entry_order_id=entry_order_id)
            return

        symbol = trade.get("symbol", "")
        sl_price = float(trade.get("stop_loss") or 0.0)

        # pct_distance = abs(current_price - sl_price) / sl_price * 100
        pct_distance = abs(current_price - sl_price) / sl_price * 100 if sl_price else 0.0

        trade_id = str(trade.get("_id", entry_order_id))

        event = SLMissingEvent(
            symbol=symbol,
            trade_id=trade_id,
            sl_price=sl_price,
            current_price=current_price,
            pct_distance=pct_distance,
            timestamp=datetime.now(UTC),
        )

        await self._notifier.send(NotificationEvent.SL_MISSING, event)

        # Marcar como notificado para evitar spam
        self._notified_sl_missing.add(entry_order_id)

        await self._repository.audit(
            "sl_missing_detected",
            {
                "entry_order_id": entry_order_id,
                "symbol": symbol,
                "sl_price": sl_price,
                "current_price": current_price,
                "pct_distance": pct_distance,
            },
        )

        logger.warning(
            "sl_missing_notified",
            symbol=symbol,
            entry_order_id=entry_order_id,
            sl_price=sl_price,
            current_price=current_price,
            pct_distance=pct_distance,
        )

    async def _handle_manual_close(self, trade: dict) -> None:
        """Trata fechamento manual: cancela ordens remanescentes e registra CLOSED_MANUAL.

        exit_price obtido via fetch_ticker — é estimado (is_estimated=True).
        """
        symbol = trade.get("symbol", "")
        entry_order_id = trade.get("entry_order_id", "")

        # Cancelar ordens remanescentes antes de atualizar status
        await self._client.cancel_all_orders(symbol)

        # exit_price via fetch_ticker (estimado — DD-005)
        exit_price: float | None = None
        try:
            ticker = await self._client.fetch_ticker(symbol)
            exit_price = float(ticker.get("last") or ticker.get("close") or 0.0)
        except Exception as exc:
            logger.warning(
                "manual_close_ticker_failed",
                symbol=symbol,
                error_type=type(exc).__name__,
            )

        pnl_usdt: float | None = None
        if exit_price:
            pnl_usdt = self._calc_pnl(trade, exit_price)

        await self._repository.update_trade_status(
            entry_order_id=entry_order_id,
            status=TradeStatus.CLOSED_MANUAL,
            exit_price=exit_price,
            pnl_usdt=pnl_usdt,
            close_reason="manual_close",
        )

        # Persistir flag is_estimated diretamente no documento
        await self._repository.database["trades"].update_one(
            {"entry_order_id": entry_order_id},
            {"$set": {"is_estimated": True}},
        )

        await self._repository.audit(
            "trade_closed_manual",
            {
                "entry_order_id": entry_order_id,
                "symbol": symbol,
                "exit_price": exit_price,
                "pnl_usdt": pnl_usdt,
                "is_estimated": True,
            },
        )

        logger.info(
            "trade_closed_manual",
            symbol=symbol,
            entry_order_id=entry_order_id,
            exit_price=exit_price,
            pnl_usdt=pnl_usdt,
        )

    async def _fetch_order_with_retry(
        self,
        order_id: str,
        symbol: str,
        retries: int = 3,
        base_delay: float = 1.0,
    ) -> dict[str, Any] | None:
        """Busca ordem com retry e backoff exponencial (padrão SPEC_007).

        Retorna None se esgotar todas as tentativas ou erro não recuperável.
        Nunca loga str(exc) — usa type(exc).__name__ (RF-011).
        Delays: base_delay * 2^(attempt-1) → 1s, 2s, 4s com base_delay=1.0.
        """
        last_exc: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                return await self._client.fetch_order(order_id, symbol)
            except _FATAL_ERRORS:
                raise
            except Exception as exc:
                last_exc = exc
                next_delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "fetch_order_retry",
                    order_id=order_id,
                    symbol=symbol,
                    attempt=attempt,
                    retries=retries,
                    error_type=type(exc).__name__,
                    next_wait_s=next_delay,
                )
                if attempt < retries:
                    await asyncio.sleep(next_delay)

        # RF-007: retries esgotados — log e retorna None para não afetar outros trades
        logger.warning(
            "fetch_order_retries_exhausted",
            order_id=order_id,
            symbol=symbol,
            retries=retries,
            error_type=type(last_exc).__name__ if last_exc else "unknown",
        )
        return None

    async def _is_position_open(self, symbol: str) -> bool:
        """Verifica se existe posição aberta na exchange para o símbolo."""
        try:
            positions = await self._client.fetch_open_positions()
            for pos in positions:
                if pos.get("symbol") == symbol:
                    return True
            return False
        except Exception as exc:
            logger.warning(
                "check_position_failed",
                symbol=symbol,
                error_type=type(exc).__name__,
            )
            # Em caso de dúvida, assume que a posição existe (conservador)
            return True

    async def _get_current_price(self, symbol: str) -> float | None:
        """Obtém o preço atual do símbolo via fetch_ticker."""
        try:
            ticker = await self._client.fetch_ticker(symbol)
            price = ticker.get("last") or ticker.get("close")
            return float(price) if price is not None else None
        except Exception as exc:
            logger.warning(
                "get_current_price_failed",
                symbol=symbol,
                error_type=type(exc).__name__,
            )
            return None

    def _calc_pnl(self, trade: dict, exit_price: float) -> float:
        """Calcula PnL em USDT para o trade.

        Fórmula: (exit_price - entry_price) * quantity * side_multiplier - fees
        side_multiplier: +1 para LONG, -1 para SHORT.
        """
        direction = trade.get("direction", "long")
        entry_price = float(trade.get("entry_price") or 0.0)
        quantity = float(trade.get("quantity") or 0.0)
        fees = float(trade.get("fees") or 0.0)
        side_mult = 1.0 if direction == "long" else -1.0
        return (exit_price - entry_price) * quantity * side_mult - fees
