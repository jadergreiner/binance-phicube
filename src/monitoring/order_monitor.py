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
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import ccxt.async_support as ccxt

from src.common.decorators import retry
from src.monitoring.logger import get_logger
from src.notifications.events import (
    NotificationEvent,
    SLMissingEvent,
    SLRestoredEvent,
)
from src.notifications.notifier import Notifier
from src.storage.repository import MongoRepository
from src.trading.order_manager import TradeStatus

logger = get_logger(__name__)

_DEFAULT_RENOTIFY_INTERVAL_SECONDS = 15 * 60  # 15 minutos

# Padrões para retry de fetch_order
_DEFAULT_ORDER_RETRIES: int = 3
_DEFAULT_ORDER_INITIAL_DELAY: float = 1.0
_DEFAULT_ORDER_BACKOFF_FACTOR: float = 2.0


@dataclass
class SLMissingState:
    """Estado em memória de uma posição com SL órfão ativo."""

    trade_id: str
    first_detected_at: datetime
    last_notified_at: datetime
    notification_count: int
    renotify_interval_seconds: int


@dataclass
class ManualClosePendingState:
    """Estado transitório para confirmação de fechamento manual."""

    missing_position_cycles: int = 0
    order_not_found_seen: bool = False


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
        client: Any,
        repository: MongoRepository,
        notifier: Notifier,
        interval_seconds: int = 60,
        renotify_interval_seconds: int = _DEFAULT_RENOTIFY_INTERVAL_SECONDS,
        manual_close_confirm_cycles: int = 3,
        manual_close_require_dual_source: bool = True,
    ) -> None:
        self._client = client
        self._repository = repository
        self._notifier = notifier
        self._interval_seconds = interval_seconds
        self._renotify_interval_seconds = renotify_interval_seconds
        self._manual_close_confirm_cycles = max(1, int(manual_close_confirm_cycles))
        self._manual_close_require_dual_source = bool(manual_close_require_dual_source)
        # Estado de re-notificação por entry_order_id. Persistido apenas em memória
        # (DD-001): em restart, um segundo primeiro-alerta é enviado — comportamento
        # aceitável e documentado (CE-003).
        self._sl_missing_state: dict[str, SLMissingState] = {}
        # Confirmação de ausência de posição para evitar CLOSED_MANUAL prematuro.
        self._manual_close_pending: dict[str, ManualClosePendingState] = {}
        self._last_fetch_order_not_found: bool = False

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
        entry_order_id = trade.get("entry_order_id", "")
        sl_order_id = trade.get("sl_order_id")
        tp_order_id = trade.get("tp_order_id")
        order_not_found_seen = False

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
                            entry_order_id = trade.get("entry_order_id", "")
                            # CE-001: SL pode ter sido restaurado manualmente
                            if entry_order_id in self._sl_missing_state:
                                has_sl = await self._has_active_stop_order(symbol)
                                if has_sl:
                                    await self._handle_sl_cleared(trade)
                                    return
                            await self._handle_sl_missing(trade, current_price)
                    # Se posição não existe mais, não alerta — já encerrada
                    return
            elif self._last_fetch_order_not_found:
                order_not_found_seen = True

        # ─── Verifica TP ─────────────────────────────────────────────────────
        if tp_order_id:
            tp_order = await self._fetch_order_with_retry(tp_order_id, symbol)

            if tp_order is not None:
                tp_status = tp_order.get("status", "")

                if tp_status == "closed":
                    # TP executado — registrar fechamento com PnL real
                    await self._handle_tp_executed(trade, tp_order)
                    return
            elif self._last_fetch_order_not_found:
                order_not_found_seen = True

        if order_not_found_seen:
            await self._repository.audit(
                "order_reference_missing",
                {
                    "entry_order_id": entry_order_id,
                    "symbol": symbol,
                    "sl_order_id": sl_order_id,
                    "tp_order_id": tp_order_id,
                },
            )

            # ─── Reconciliação com a exchange ─────────────────────────────────
            # IDs armazenados falharam mas as ordens podem existir na exchange
            # com IDs diferentes (ex: API key rotacionada). Buscar ordens abertas
            # e reconciliar os IDs no MongoDB.
            reconciled = await self._reconcile_orders(trade, symbol)
            if reconciled:
                # Re-verificar trade com IDs reconciliados (1 nível apenas)
                await self._check_trade(reconciled)
                return

            # Reconciliação falhou — ordens de proteção não existem na exchange.
            # Se a posição ainda está aberta, alertar operador sobre SL ausente.
            # _handle_sl_missing gerencia renotificação internamente.
            if sl_order_id:
                current_price = await self._get_current_price(symbol)
                if current_price is not None:
                    position_open = await self._is_position_open(symbol)
                    if position_open:
                        await self._handle_sl_missing(trade, current_price)
                        return

        # ─── Verifica fechamento manual ───────────────────────────────────────
        position_open_source_a = await self._is_position_open(symbol)
        position_open_source_b = await self._is_position_open_risk(symbol)
        dual_source_absent = (not position_open_source_a) and (not position_open_source_b)
        should_confirm_absent = (
            dual_source_absent
            if self._manual_close_require_dual_source
            else (not position_open_source_a)
        )

        if not should_confirm_absent:
            if order_not_found_seen and (position_open_source_a or position_open_source_b):
                logger.info(
                    "manual_close_prevented_due_to_open_position",
                    symbol=symbol,
                    entry_order_id=entry_order_id,
                    position_check_source_a=position_open_source_a,
                    position_check_source_b=position_open_source_b,
                    order_not_found_seen=order_not_found_seen,
                )
                await self._repository.audit(
                    "manual_close_prevented_due_to_open_position",
                    {
                        "entry_order_id": entry_order_id,
                        "symbol": symbol,
                        "position_check_source_a": position_open_source_a,
                        "position_check_source_b": position_open_source_b,
                        "order_not_found_seen": order_not_found_seen,
                    },
                )
            self._manual_close_pending.pop(entry_order_id, None)
            return

        pending = self._manual_close_pending.get(entry_order_id, ManualClosePendingState())
        pending.missing_position_cycles += 1
        pending.order_not_found_seen = pending.order_not_found_seen or order_not_found_seen
        self._manual_close_pending[entry_order_id] = pending
        await self._repository.audit(
            "reconciliation_pending_manual_close",
            {
                "entry_order_id": entry_order_id,
                "symbol": symbol,
                "missing_position_cycles": pending.missing_position_cycles,
                "required_cycles": self._manual_close_confirm_cycles,
                "position_check_source_a": position_open_source_a,
                "position_check_source_b": position_open_source_b,
                "order_not_found_seen": pending.order_not_found_seen,
                "manual_close_decision_basis": {
                    "require_dual_source": self._manual_close_require_dual_source,
                    "dual_source_absent": dual_source_absent,
                    "result": (
                        "pending"
                        if pending.missing_position_cycles < self._manual_close_confirm_cycles
                        else "confirm_manual_close"
                    ),
                },
            },
        )
        if pending.missing_position_cycles < self._manual_close_confirm_cycles:
            await self._repository.audit(
                "manual_close_confirmation_pending",
                {
                    "entry_order_id": entry_order_id,
                    "symbol": symbol,
                    "missing_position_cycles": pending.missing_position_cycles,
                    "required_cycles": self._manual_close_confirm_cycles,
                    "position_check_source_a": position_open_source_a,
                    "position_check_source_b": position_open_source_b,
                    "order_not_found_seen": pending.order_not_found_seen,
                },
            )
            logger.info(
                "manual_close_confirmation_pending",
                symbol=symbol,
                entry_order_id=entry_order_id,
                missing_position_cycles=pending.missing_position_cycles,
                required_cycles=self._manual_close_confirm_cycles,
                position_check_source_a=position_open_source_a,
                position_check_source_b=position_open_source_b,
                order_not_found_seen=pending.order_not_found_seen,
            )
            return

        # Posição ausente por N ciclos consecutivos -> fechamento manual confirmado.
        await self._handle_manual_close(trade)
        self._manual_close_pending.pop(entry_order_id, None)

    async def _handle_tp_executed(self, trade: dict, order: dict) -> None:
        """Registra encerramento por TP com exit_price real."""
        symbol = trade.get("symbol", "")
        entry_order_id = trade.get("entry_order_id", "")

        await self._handle_sl_cleared(trade)

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

        await self._handle_sl_cleared(trade)

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
        """Re-notificação periódica de SL ausente (RF-001, RF-002, RF-003).

        Primeiro alerta: cria estado e persiste first_detected_at no MongoDB.
        Re-alertas: enviados a cada `_renotify_interval_seconds` enquanto órfão.
        """
        entry_order_id = trade.get("entry_order_id", "")
        now = datetime.now(UTC)
        symbol = trade.get("symbol", "")
        sl_price = float(trade.get("stop_loss") or 0.0)
        pct_distance = abs(current_price - sl_price) / sl_price * 100 if sl_price else 0.0
        trade_id = str(trade.get("_id", entry_order_id))

        if entry_order_id not in self._sl_missing_state:
            # ── Primeira detecção ────────────────────────────────────────────
            state = SLMissingState(
                trade_id=trade_id,
                first_detected_at=now,
                last_notified_at=now,
                notification_count=1,
                renotify_interval_seconds=self._renotify_interval_seconds,
            )
            self._sl_missing_state[entry_order_id] = state

            try:
                await self._repository.update_sl_orphan_first_detected(
                    entry_order_id=entry_order_id,
                    first_detected_at=now,
                )
            except Exception as exc:
                logger.warning(
                    "sl_orphan_first_detected_persist_failed",
                    error_type=type(exc).__name__,
                )

            event = SLMissingEvent(
                symbol=symbol,
                trade_id=trade_id,
                sl_price=sl_price,
                current_price=current_price,
                pct_distance=pct_distance,
                timestamp=now,
                notification_count=1,
                time_unprotected_seconds=0,
            )
            await self._notifier.send(NotificationEvent.SL_MISSING, event)

            await self._repository.audit(
                "sl_missing_detected",
                {
                    "entry_order_id": entry_order_id,
                    "symbol": symbol,
                    "sl_price": sl_price,
                    "current_price": current_price,
                    "pct_distance": pct_distance,
                    "notification_count": 1,
                },
            )

            logger.warning(
                "sl_missing_first_alert",
                symbol=symbol,
                entry_order_id=entry_order_id,
                sl_price=sl_price,
            )
            return

        # ── Re-notificação: checar se intervalo passou ────────────────────────
        state = self._sl_missing_state[entry_order_id]
        elapsed = (now - state.last_notified_at).total_seconds()

        if elapsed < state.renotify_interval_seconds:
            logger.debug(
                "sl_missing_renotify_wait",
                entry_order_id=entry_order_id,
                elapsed_s=int(elapsed),
                wait_s=int(state.renotify_interval_seconds - elapsed),
            )
            return

        new_count = state.notification_count + 1
        time_unprotected = int((now - state.first_detected_at).total_seconds())
        state.notification_count = new_count
        state.last_notified_at = now

        event = SLMissingEvent(
            symbol=symbol,
            trade_id=trade_id,
            sl_price=sl_price,
            current_price=current_price,
            pct_distance=pct_distance,
            timestamp=now,
            notification_count=new_count,
            time_unprotected_seconds=time_unprotected,
        )
        await self._notifier.send(NotificationEvent.SL_MISSING, event)

        await self._repository.audit(
            "sl_missing_renotified",
            {
                "entry_order_id": entry_order_id,
                "symbol": symbol,
                "notification_count": new_count,
                "time_unprotected_seconds": time_unprotected,
            },
        )

        logger.warning(
            "sl_missing_renotified",
            symbol=symbol,
            entry_order_id=entry_order_id,
            notification_count=new_count,
            time_unprotected_seconds=time_unprotected,
        )

    async def _handle_sl_cleared(self, trade: dict) -> None:
        """Registra resolução de SL órfão (RF-004, RF-005, RF-007).

        Chamado quando a posição fecha (TP/SL/manual) ou SL é restaurado
        manualmente enquanto a posição ainda está aberta (CE-001).
        Noop se o trade não estava em estado de SL órfão.
        """
        entry_order_id = trade.get("entry_order_id", "")
        if entry_order_id not in self._sl_missing_state:
            return

        state = self._sl_missing_state.pop(entry_order_id)
        now = datetime.now(UTC)
        response_time = int((now - state.first_detected_at).total_seconds())
        symbol = trade.get("symbol", "")

        try:
            await self._repository.update_sl_orphan_metrics(
                entry_order_id=entry_order_id,
                sl_restored_at=now,
                response_time_seconds=response_time,
                notification_count=state.notification_count,
            )
        except Exception as exc:
            logger.warning(
                "sl_orphan_metrics_persist_failed",
                error_type=type(exc).__name__,
            )

        event = SLRestoredEvent(
            symbol=symbol,
            trade_id=state.trade_id,
            response_time_seconds=response_time,
            notification_count=state.notification_count,
            timestamp=now,
        )
        await self._notifier.send(NotificationEvent.SL_RESTORED, event)

        await self._repository.audit(
            "sl_missing_cleared",
            {
                "entry_order_id": entry_order_id,
                "symbol": symbol,
                "response_time_seconds": response_time,
                "notification_count": state.notification_count,
            },
        )

        logger.info(
            "sl_missing_cleared",
            symbol=symbol,
            entry_order_id=entry_order_id,
            response_time_seconds=response_time,
            notification_count=state.notification_count,
        )

    async def _has_active_stop_order(self, symbol: str) -> bool:
        """Verifica se há ordem stop ativa para o símbolo (CE-001).

        Conservador: retorna False em caso de falha, nunca silencia um alerta.
        """
        try:
            orders = await self._client.fetch_open_orders(symbol)
            return any(
                o.get("type", "").lower() in ("stop_market", "stop", "stop_loss") for o in orders
            )
        except Exception as exc:
            logger.warning(
                "check_stop_order_failed",
                symbol=symbol,
                error_type=type(exc).__name__,
            )
            return False

    async def _reconcile_orders(self, trade: dict, symbol: str) -> dict | None:
        """Reconcilia ordens SL/TP via fetch_open_orders quando IDs armazenados
        falham (OrderNotFound). A fonte da verdade é a exchange — atualiza o
        MongoDB com os IDs reais das ordens abertas.

        Retorna o trade atualizado ou None se não conseguir reconciliar.
        """
        entry_order_id = trade.get("entry_order_id", "")
        direction = trade.get("direction", "long")
        is_long = direction == "long"
        exit_side = "sell" if is_long else "buy"

        try:
            open_orders = await self._client.fetch_open_orders(symbol)
        except Exception as exc:
            logger.warning(
                "reconcile_open_orders_failed",
                symbol=symbol,
                error_type=type(exc).__name__,
            )
            return None

        if not open_orders:
            return None

        new_sl_order_id: str | None = None
        new_tp_order_id: str | None = None

        for order in open_orders:
            o_type = str(order.get("type", "")).lower()
            o_side = str(order.get("side", "")).lower()

            if o_side != exit_side:
                continue

            if o_type in ("stop_market", "stop", "stop_loss"):
                if new_sl_order_id is None:
                    new_sl_order_id = str(order.get("id", ""))
            elif o_type in ("take_profit_market", "take_profit"):
                if new_tp_order_id is None:
                    new_tp_order_id = str(order.get("id", ""))

        if new_sl_order_id is None and new_tp_order_id is None:
            return None

        original_sl = trade.get("sl_order_id")
        original_tp = trade.get("tp_order_id")

        if (new_sl_order_id and new_sl_order_id != original_sl) or (
            new_tp_order_id and new_tp_order_id != original_tp
        ):
            sl_to_update = (
                new_sl_order_id if new_sl_order_id and new_sl_order_id != original_sl else None
            )
            tp_to_update = (
                new_tp_order_id if new_tp_order_id and new_tp_order_id != original_tp else None
            )

            await self._repository.update_trade_orders(
                entry_order_id=entry_order_id,
                sl_order_id=sl_to_update,
                tp_order_id=tp_to_update,
            )

            logger.info(
                "trade_orders_reconciled",
                symbol=symbol,
                entry_order_id=entry_order_id,
                sl_order_id=new_sl_order_id,
                tp_order_id=new_tp_order_id,
            )

            await self._repository.audit(
                "trade_orders_reconciled",
                {
                    "entry_order_id": entry_order_id,
                    "symbol": symbol,
                    "previous_sl_order_id": original_sl,
                    "new_sl_order_id": new_sl_order_id,
                    "previous_tp_order_id": original_tp,
                    "new_tp_order_id": new_tp_order_id,
                },
            )

        trade["sl_order_id"] = new_sl_order_id or original_sl
        trade["tp_order_id"] = new_tp_order_id or original_tp
        return trade

    async def _handle_manual_close(self, trade: dict) -> None:
        """Trata fechamento manual: cancela ordens remanescentes e registra CLOSED_MANUAL.

        exit_price obtido via fetch_ticker — é estimado (is_estimated=True).
        """
        symbol = trade.get("symbol", "")
        entry_order_id = trade.get("entry_order_id", "")

        await self._handle_sl_cleared(trade)

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
                "manual_close_confirmed_cycles": self._manual_close_confirm_cycles,
            },
        )

        logger.info(
            "trade_closed_manual",
            symbol=symbol,
            entry_order_id=entry_order_id,
            exit_price=exit_price,
            pnl_usdt=pnl_usdt,
        )

    @retry(
        max_attempts=_DEFAULT_ORDER_RETRIES,
        initial_delay=_DEFAULT_ORDER_INITIAL_DELAY,
        backoff_factor=_DEFAULT_ORDER_BACKOFF_FACTOR,
        exc_types=(Exception,),
        fatal_exc_types=_FATAL_ERRORS,
        fallback=None,
        log_event_prefix="fetch_order",
    )
    async def _fetch_order_core(
        self,
        order_id: str,
        symbol: str,
    ) -> dict[str, Any] | None:
        """Método interno decorado com @retry para fetch_order.

        Trata ccxt.OrderNotFound internamente com side effects (log + estado).
        Não use diretamente — use _fetch_order_with_retry() para compatibilidade.
        """
        try:
            self._last_fetch_order_not_found = False
            return await self._client.fetch_order(order_id, symbol)
        except ccxt.OrderNotFound:
            # Ordem pode já ter saído da janela de consulta da exchange.
            # Não é erro fatal para o monitor: seguimos com fallback
            # de reconciliação por posição aberta/fechada.
            logger.info(
                "fetch_order_not_found",
                order_id=order_id,
                symbol=symbol,
            )
            self._last_fetch_order_not_found = True
            return None

    async def _fetch_order_with_retry(
        self,
        order_id: str,
        symbol: str,
        retries: int | None = None,
        base_delay: float | None = None,
    ) -> dict[str, Any] | None:
        """Busca ordem com retry e backoff exponencial (padrão SPEC_007).

        Usa @retry decorador centralizado de src.common.decorators.

        Parâmetros DEPRECADOS (mantidos para compatibilidade):
        - retries: Ignorado — usa padrão {_DEFAULT_ORDER_RETRIES} tentativas
        - base_delay: Ignorado — usa padrão {_DEFAULT_ORDER_INITIAL_DELAY}s

        Comportamento:
        - Backoff exponencial: 1s, 2s, 4s
        - ccxt.OrderNotFound: retorna None com log INFO (não é erro)
        - Erros fatais (AuthenticationError, InsufficientFunds, etc): raise imediato
        - Outros erros: retry até esgotar, depois retorna None
        - Nunca loga str(exc) — usa error_type=type(exc).__name__

        Args:
            order_id: ID da ordem para buscar
            symbol: Par de trading
            retries: DEPRECATED — ignorado
            base_delay: DEPRECATED — ignorado

        Returns:
            Dict com dados da ordem, ou None se não encontrada ou retries esgotados

        Raises:
            ccxt.AuthenticationError, ccxt.InsufficientFunds, etc: Erros fatais
        """
        # Aviso se parâmetros deprecated forem usados
        if retries is not None or base_delay is not None:
            logger.debug(
                "fetch_order_deprecated_params_ignored",
                retries=retries,
                base_delay=base_delay,
            )

        return await self._fetch_order_core(order_id, symbol)

    async def _is_position_open(self, symbol: str) -> bool:
        """Verifica se existe posição aberta na exchange para o símbolo."""
        try:
            target = self._normalize_symbol(symbol)
            positions = await self._client.fetch_open_positions()
            for pos in positions:
                if self._normalize_symbol(str(pos.get("symbol", ""))) == target:
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

    async def _is_position_open_risk(self, symbol: str) -> bool:
        """Fonte secundária: posição aberta por position risk (posição != 0)."""
        try:
            target = self._normalize_symbol(symbol)
            positions = await self._client.fetch_position_risk(symbol=symbol)
            for pos in positions:
                if self._normalize_symbol(str(pos.get("symbol", ""))) != target:
                    continue
                amount = pos.get("positionAmt", pos.get("contracts", 0))
                try:
                    if abs(float(amount or 0.0)) > 0.0:
                        return True
                except (TypeError, ValueError):
                    continue
            return False
        except Exception as exc:
            logger.warning(
                "check_position_risk_failed",
                symbol=symbol,
                error_type=type(exc).__name__,
            )
            # Em caso de dúvida, assume posição aberta (conservador)
            return True

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Normaliza símbolo para comparação semântica (ex: ATOMUSDT == ATOM/USDT:USDT)."""
        normalized = symbol.upper().replace("/", "").replace(":", "")
        if normalized.endswith("USDTUSDT"):
            return normalized[:-4]
        return normalized

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
