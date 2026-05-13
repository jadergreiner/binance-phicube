"""
ResilientMongoRepository — Wrapper de resiliência sobre MongoRepository.

Implementa Circuit Breaker com recovery_timeout=60s, retry 3x para Tipo B,
graceful degrade para Tipo C, e integração com PendingTradesJournal para
trades não-persistidos.

Padrão: Facade + Circuit Breaker + Retry + Journal.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from src.monitoring.logger import get_logger
from src.resilience.circuit_breaker import CircuitBreakerRegistry, CircuitBreakerState
from src.storage.pending_trades_journal import PendingTradesJournal

if TYPE_CHECKING:
    from src.notifications.notifier import Notifier
    from src.storage.repository import MongoRepository
    from src.trading.order_manager import Trade

logger = get_logger(__name__)

# Constantes de retry/backoff
_RETRY_ATTEMPTS = 3
_BACKOFF_DELAYS = [0.1, 0.2, 0.4]  # em segundos: 100ms, 200ms, 400ms
_TIMEOUT_SECS = 5.0

# Namespaces de circuit breaker
_CB_NAMESPACE_MONGODB = "mongodb"
_CB_NAME_SAVE_TRADE = f"{_CB_NAMESPACE_MONGODB}:save_trade"
_CB_NAME_SAVE_SIGNAL = f"{_CB_NAMESPACE_MONGODB}:save_signal"
_CB_NAME_AUDIT_LOG = f"{_CB_NAMESPACE_MONGODB}:audit_log"
_CB_NAME_INSERT_ONE = f"{_CB_NAMESPACE_MONGODB}:insert_one"


class ResilientMongoRepository:
    """Wrapper resiliente sobre MongoRepository com CB + retry + journal."""

    def __init__(
        self,
        real_repo: MongoRepository,
        notifier: Notifier,
        cb_registry: CircuitBreakerRegistry | None = None,
        recovery_timeout_secs: float | None = None,
        journal: PendingTradesJournal | None = None,
    ) -> None:
        """
        Inicializa o ResilientMongoRepository.

        Args:
            real_repo: Instância de MongoRepository (composição).
            notifier: Notifier para alertas (Telegram).
            cb_registry: CircuitBreakerRegistry (default: novo com namespace='mongodb').
            recovery_timeout_secs: Timeout de recovery do CB (default: 60s).
            journal: PendingTradesJournal (default: nova instância padrão).
        """
        self._real_repo = real_repo
        self._notifier = notifier
        self._cb_registry = cb_registry or CircuitBreakerRegistry(namespace=_CB_NAMESPACE_MONGODB)
        self._recovery_timeout_secs = recovery_timeout_secs or 60.0
        self._journal = journal or PendingTradesJournal()

    async def save_trade(self, trade: Trade) -> str | None:
        """
        Salva trade no MongoDB com retry 3x (Tipo B).

        Se falhar 3x, escreve em PendingTradesJournal e retorna Ok.
        Nunca levanta exceção — sempre retorna None ou doc_id.

        Backoff: 100ms, 200ms, 400ms = 700ms total antes de abort.

        Args:
            trade: Trade a salvar.

        Returns:
            doc_id (string) se sucesso, None se falha 3x (mas journaled).
        """
        cb = self._cb_registry.get(
            _CB_NAME_SAVE_TRADE,
            recovery_timeout=self._recovery_timeout_secs,
        )

        # Se CB está OPEN, tenta HALF_OPEN
        if cb.state == CircuitBreakerState.OPEN:
            cb.attempt_half_open()

        # Se CB ainda está OPEN, retorna None (não tenta)
        if cb.state == CircuitBreakerState.OPEN:
            logger.warning(
                "save_trade_circuit_breaker_open",
                cb_name=_CB_NAME_SAVE_TRADE,
                recovery_timeout_secs=self._recovery_timeout_secs,
            )
            # Journala como fallback
            try:
                await self._journal.add_trade(trade)
                logger.info(
                    "save_trade_journaled_due_to_open_cb",
                    entry_order_id=trade.entry_order_id,
                )
            except Exception as exc:
                logger.error(
                    "save_trade_journal_fallback_failed",
                    entry_order_id=trade.entry_order_id,
                    error=type(exc).__name__,
                )
            return None

        # Retry loop: 3x com backoff
        last_exc: Exception | None = None
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                result = await asyncio.wait_for(
                    self._real_repo.save_trade(trade),
                    timeout=_TIMEOUT_SECS,
                )
                # Sucesso — registra no CB
                cb.record_success()
                logger.info(
                    "save_trade_succeeded",
                    entry_order_id=trade.entry_order_id,
                    attempt=attempt + 1,
                )
                return result
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "save_trade_attempt_failed",
                    entry_order_id=trade.entry_order_id,
                    attempt=attempt + 1,
                    error=type(exc).__name__,
                )
                # Registra falha no CB
                cb.record_failure()
                # Backoff antes de próxima tentativa
                if attempt < _RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(_BACKOFF_DELAYS[attempt])

        # Falhou 3x — journala e envia alerta
        logger.error(
            "save_trade_failed_after_retries",
            entry_order_id=trade.entry_order_id,
            attempts=_RETRY_ATTEMPTS,
            last_error=type(last_exc).__name__ if last_exc else "unknown",
        )

        # Journala para reprocessamento posterior
        try:
            await self._journal.add_trade(trade)
            logger.info("save_trade_journaled_after_failures", entry_order_id=trade.entry_order_id)
        except Exception as journal_exc:
            logger.error(
                "save_trade_journal_write_failed",
                entry_order_id=trade.entry_order_id,
                error=type(journal_exc).__name__,
            )

        # Envia Telegram alert
        await self._send_alert(
            f"🚨 **Erro ao salvar trade no MongoDB**\n"
            f"Entry Order ID: {trade.entry_order_id}\n"
            f"Símbolo: {trade.symbol}\n"
            f"Tentativas: {_RETRY_ATTEMPTS}\n"
            f"Status: Journaled para reprocessamento"
        )

        return None

    async def save_signal(self, signal_dict: dict) -> str | None:
        """
        Salva signal no MongoDB com graceful degrade (Tipo C).

        Se falha, retorna Ok (não retenta).

        Args:
            signal_dict: Dicionário de signal.

        Returns:
            doc_id (string) se sucesso, None se falha.
        """
        cb = self._cb_registry.get(
            _CB_NAME_SAVE_SIGNAL,
            recovery_timeout=self._recovery_timeout_secs,
        )

        # Se CB está OPEN, não tenta
        if cb.state == CircuitBreakerState.OPEN:
            cb.attempt_half_open()
            if cb.state == CircuitBreakerState.OPEN:
                logger.warning(
                    "save_signal_circuit_breaker_open",
                    cb_name=_CB_NAME_SAVE_SIGNAL,
                )
                return None

        # Tenta 1x (Tipo C — graceful degrade)
        try:
            result = await asyncio.wait_for(
                self._real_repo.save_signal(signal_dict),
                timeout=_TIMEOUT_SECS,
            )
            cb.record_success()
            logger.info("save_signal_succeeded")
            return result
        except Exception as exc:
            cb.record_failure()
            logger.warning(
                "save_signal_failed",
                error=type(exc).__name__,
                signal_symbol=signal_dict.get("symbol"),
            )
            return None

    async def audit_log(self, event_name: str, data: dict[str, Any]) -> None:
        """
        Registra log de auditoria com retry 3x (Tipo B).

        Se falha 3x, envia Telegram alert mas não levanta exceção.

        Args:
            event_name: Nome do evento.
            data: Dados do evento.
        """
        cb = self._cb_registry.get(
            _CB_NAME_AUDIT_LOG,
            recovery_timeout=self._recovery_timeout_secs,
        )

        # Se CB está OPEN, tenta HALF_OPEN
        if cb.state == CircuitBreakerState.OPEN:
            cb.attempt_half_open()

        # Se CB ainda está OPEN, apenas loga e retorna
        if cb.state == CircuitBreakerState.OPEN:
            logger.warning(
                "audit_log_circuit_breaker_open",
                cb_name=_CB_NAME_AUDIT_LOG,
                event_name=event_name,
            )
            return

        # Retry loop: 3x com backoff
        last_exc: Exception | None = None
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                await asyncio.wait_for(
                    self._real_repo.audit(event_name, data),
                    timeout=_TIMEOUT_SECS,
                )
                cb.record_success()
                logger.info("audit_log_succeeded", event_name=event_name, attempt=attempt + 1)
                return
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "audit_log_attempt_failed",
                    event_name=event_name,
                    attempt=attempt + 1,
                    error=type(exc).__name__,
                )
                cb.record_failure()
                # Backoff
                if attempt < _RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(_BACKOFF_DELAYS[attempt])

        # Falhou 3x — envia alert
        logger.error(
            "audit_log_failed_after_retries",
            event_name=event_name,
            attempts=_RETRY_ATTEMPTS,
            last_error=type(last_exc).__name__ if last_exc else "unknown",
        )

        await self._send_alert(
            f"⚠️ **Erro ao registrar auditoria**\n"
            f"Evento: {event_name}\n"
            f"Tentativas: {_RETRY_ATTEMPTS}\n"
            f"Status: Não foi registrado"
        )

    async def insert_one(self, collection_name: str, doc: dict[str, Any]) -> str | None:
        """
        Insere um documento genérico com retry 3x (Tipo B).

        Se falha 3x, retorna None (não levanta exceção).

        Args:
            collection_name: Nome da coleção.
            doc: Documento a inserir.

        Returns:
            doc_id (string) se sucesso, None se falha 3x.
        """
        cb = self._cb_registry.get(
            _CB_NAME_INSERT_ONE,
            recovery_timeout=self._recovery_timeout_secs,
        )

        # Se CB está OPEN, tenta HALF_OPEN
        if cb.state == CircuitBreakerState.OPEN:
            cb.attempt_half_open()

        # Se CB ainda está OPEN, retorna None
        if cb.state == CircuitBreakerState.OPEN:
            logger.warning(
                "insert_one_circuit_breaker_open",
                cb_name=_CB_NAME_INSERT_ONE,
                collection=collection_name,
            )
            return None

        # Retry loop: 3x com backoff
        last_exc: Exception | None = None
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                result = await asyncio.wait_for(
                    self._real_repo.database[collection_name].insert_one(doc),
                    timeout=_TIMEOUT_SECS,
                )
                cb.record_success()
                doc_id = str(result.inserted_id)
                logger.info(
                    "insert_one_succeeded",
                    collection=collection_name,
                    doc_id=doc_id,
                    attempt=attempt + 1,
                )
                return doc_id
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "insert_one_attempt_failed",
                    collection=collection_name,
                    attempt=attempt + 1,
                    error=type(exc).__name__,
                )
                cb.record_failure()
                # Backoff
                if attempt < _RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(_BACKOFF_DELAYS[attempt])

        # Falhou 3x
        logger.error(
            "insert_one_failed_after_retries",
            collection=collection_name,
            attempts=_RETRY_ATTEMPTS,
            last_error=type(last_exc).__name__ if last_exc else "unknown",
        )
        return None

    # ─── Métodos passthroughs (sem resiliência) ────────────────────────────────

    @property
    def database(self) -> Any:
        """Expõe database da repo real para acesso direto se necessário."""
        return self._real_repo.database

    async def setup_indexes(self) -> None:
        """Delegate para setup de índices."""
        await self._real_repo.setup_indexes()

    async def close(self) -> None:
        """Delegate para fecha mongo."""
        await self._real_repo.close()

    async def get_open_trades(self) -> list[dict]:
        """Delegate: lista trades abertos."""
        return await self._real_repo.get_open_trades()

    async def get_open_trades_for_symbol(self, symbol: str) -> list[dict]:
        """Delegate: lista trades abertos de um símbolo."""
        return await self._real_repo.get_open_trades_for_symbol(symbol)

    async def count_open_trades(self) -> int:
        """Delegate: conta trades abertos."""
        return await self._real_repo.count_open_trades()

    async def get_performance_metrics(self) -> dict[str, float | int]:
        """Delegate: métricas de performance."""
        return await self._real_repo.get_performance_metrics()

    async def get_performance_by_symbol(self) -> dict[str, dict]:
        """Delegate: performance por símbolo."""
        return await self._real_repo.get_performance_by_symbol()

    async def get_performance_by_timeframe(self) -> dict[str, dict]:
        """Delegate: performance por timeframe."""
        return await self._real_repo.get_performance_by_timeframe()

    async def get_trade_history(self, limit: int = 50) -> list[dict]:
        """Delegate: histórico de trades."""
        return await self._real_repo.get_trade_history(limit)

    async def get_intraday_realized_pnl_usdt(self, now: Any = None) -> float:
        """Delegate: PnL realizado intraday."""
        return await self._real_repo.get_intraday_realized_pnl_usdt(now)

    async def get_trade_by_entry_order_id(self, entry_order_id: str) -> dict[str, Any] | None:
        """Delegate: busca trade por entry_order_id."""
        return await self._real_repo.get_trade_by_entry_order_id(entry_order_id)

    async def update_trade_status(
        self,
        entry_order_id: str,
        status: Any,
        pnl: float | None = None,
        exit_price: float | None = None,
        pnl_usdt: float | None = None,
        close_reason: str | None = None,
    ) -> None:
        """Delegate: atualiza status de trade."""
        await self._real_repo.update_trade_status(
            entry_order_id=entry_order_id,
            status=status,
            pnl=pnl,
            exit_price=exit_price,
            pnl_usdt=pnl_usdt,
            close_reason=close_reason,
        )

    async def update_sl_orphan_first_detected(
        self,
        entry_order_id: str,
        first_detected_at: Any,
    ) -> None:
        """Delegate: registra primeiro alerta de SL órfão."""
        await self._real_repo.update_sl_orphan_first_detected(entry_order_id, first_detected_at)

    async def update_sl_orphan_metrics(
        self,
        entry_order_id: str,
        sl_restored_at: Any,
        response_time_seconds: int,
        notification_count: int,
    ) -> None:
        """Delegate: registra métricas de resolução de SL órfão."""
        await self._real_repo.update_sl_orphan_metrics(
            entry_order_id, sl_restored_at, response_time_seconds, notification_count
        )

    async def update_trade_orders(
        self,
        entry_order_id: str,
        *,
        sl_order_id: str | None = None,
        tp_order_id: str | None = None,
    ) -> None:
        """Delegate: atualiza IDs de SL/TP."""
        await self._real_repo.update_trade_orders(
            entry_order_id, sl_order_id=sl_order_id, tp_order_id=tp_order_id
        )

    async def get_open_trade_sl_tp(self) -> dict[str, dict[str, float | None]]:
        """Delegate: retorna SL/TP de trades abertos."""
        return await self._real_repo.get_open_trade_sl_tp()

    async def get_last_heartbeat_at(self) -> Any:
        """Delegate: último heartbeat."""
        return await self._real_repo.get_last_heartbeat_at()

    async def get_last_bot_activity_at(self) -> Any:
        """Delegate: última atividade do bot."""
        return await self._real_repo.get_last_bot_activity_at()

    async def list_customers(self, limit: int = 50, skip: int = 0) -> list[dict[str, Any]]:
        """Delegate: lista clientes."""
        return await self._real_repo.list_customers(limit, skip)

    async def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        """Delegate: busca cliente."""
        return await self._real_repo.get_customer(customer_id)

    async def create_customer(self, customer: dict[str, Any]) -> str | None:
        """Delegate: cria cliente."""
        return await self._real_repo.create_customer(customer)

    async def update_customer(self, customer_id: str, update: dict[str, Any]) -> bool:
        """Delegate: atualiza cliente."""
        return await self._real_repo.update_customer(customer_id, update)

    async def delete_customer(self, customer_id: str) -> bool:
        """Delegate: deleta cliente."""
        return await self._real_repo.delete_customer(customer_id)

    async def count_customers(self) -> int:
        """Delegate: conta clientes."""
        return await self._real_repo.count_customers()

    async def create_onboarding_session(self, doc: dict[str, Any]) -> None:
        """Delegate: cria sessão de onboarding."""
        await self._real_repo.create_onboarding_session(doc)

    async def get_onboarding_session(self, symbol: str) -> dict[str, Any] | None:
        """Delegate: busca sessão de onboarding."""
        return await self._real_repo.get_onboarding_session(symbol)

    async def list_onboarding_sessions(self) -> list[dict[str, Any]]:
        """Delegate: lista sessões de onboarding."""
        return await self._real_repo.list_onboarding_sessions()

    async def update_onboarding_session(self, symbol: str, update: dict[str, Any]) -> None:
        """Delegate: atualiza sessão de onboarding."""
        await self._real_repo.update_onboarding_session(symbol, update)

    async def delete_onboarding_session(self, symbol: str) -> bool:
        """Delegate: deleta sessão de onboarding."""
        return await self._real_repo.delete_onboarding_session(symbol)

    async def create_backtest_job(self, doc: dict[str, Any]) -> None:
        """Delegate: cria job de backtest."""
        await self._real_repo.create_backtest_job(doc)

    async def get_backtest_job(self, job_id: str) -> dict[str, Any] | None:
        """Delegate: busca job de backtest."""
        return await self._real_repo.get_backtest_job(job_id)

    async def get_active_backtest_job_by_key(self, idempotency_key: str) -> dict[str, Any] | None:
        """Delegate: busca job de backtest ativo."""
        return await self._real_repo.get_active_backtest_job_by_key(idempotency_key)

    async def update_backtest_job(self, job_id: str, update: dict[str, Any]) -> bool:
        """Delegate: atualiza job de backtest."""
        return await self._real_repo.update_backtest_job(job_id, update)

    async def update_signal_execution_outcome(
        self,
        signal_id: str,
        *,
        execution_status: str,
        execution_reason: str | None = None,
        execution_details: dict[str, Any] | None = None,
        trade_id: str | None = None,
        outcome_at: Any = None,
    ) -> bool:
        """Delegate: atualiza resultado de execução de signal."""
        return await self._real_repo.update_signal_execution_outcome(
            signal_id,
            execution_status=execution_status,
            execution_reason=execution_reason,
            execution_details=execution_details,
            trade_id=trade_id,
            outcome_at=outcome_at,
        )

    async def get_signal_history(self, limit: int = 50) -> list[dict]:
        """Delegate: histórico de signals."""
        return await self._real_repo.get_signal_history(limit)

    async def get_latest_signal_diagnostics(self, limit: int = 10) -> list[dict]:
        """Delegate: diagnóstico de signals recentes."""
        return await self._real_repo.get_latest_signal_diagnostics(limit)

    # ─── Private methods ───────────────────────────────────────────────────────

    async def _send_alert(self, message: str) -> None:
        """Envia alert via Notifier (Telegram)."""
        try:
            from src.notifications.events import NotificationEvent

            # Cria um payload simples com a mensagem
            payload = type("Alert", (), {"to_message": lambda: message})()
            await self._notifier.send(NotificationEvent.CRITICAL_ERROR, payload)
        except Exception as exc:
            logger.warning(
                "alert_send_failed",
                error=type(exc).__name__,
            )
