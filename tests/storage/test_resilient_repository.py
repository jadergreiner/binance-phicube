"""
Testes para ResilientMongoRepository — Facade + Circuit Breaker + Retry + Journal.

Validações de TASK_034_03:
- ✓ save_trade com CB aberto retenta 3x com backoff (100ms, 200ms, 400ms)
- ✓ save_trade falha 3x → journaled em PendingTradesJournal, retorna Ok
- ✓ save_signal com CB aberto retorna Ok (graceful degrade)
- ✓ audit_log retenta 3x; falha 3x → Telegram alert
- ✓ insert_one retenta 3x; genérico funciona
- ✓ PendingTradesJournal.add_trade() é chamado após 3ª falha de save_trade
- ✓ recovery_timeout_secs de 60s é respeitado
- ✓ Backoff: 100ms + 200ms + 400ms = 700ms total antes de abort
- ✓ Sem exceção levantada em save_trade (mesmo com todas as tentativas falhando)
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.notifications.events import NotificationEvent
from src.resilience.circuit_breaker import CircuitBreakerRegistry, CircuitBreakerState
from src.storage.pending_trades_journal import PendingTradesJournal
from src.storage.resilient_repository import ResilientMongoRepository
from src.trading.order_manager import Direction, Trade, TradeStatus


def _make_trade(
    entry_order_id: str = "order_123",
    symbol: str = "BTCUSDT",
    status: TradeStatus = TradeStatus.OPEN,
) -> Trade:
    """Factory para criar trades de teste."""
    return Trade(
        entry_order_id=entry_order_id,
        symbol=symbol,
        timeframe="15m",
        direction=Direction.LONG,
        quantity=0.01,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        status=status,
        opened_at=datetime.now(UTC),
        risk_amount=10.0,
        margin_used=100.0,
    )


def _make_real_repo() -> MagicMock:
    """Cria mock de MongoRepository."""
    return MagicMock()


def _make_notifier() -> MagicMock:
    """Cria mock de Notifier."""
    notifier = AsyncMock()
    notifier.send = AsyncMock(return_value=True)
    return notifier


@pytest.mark.asyncio
class TestSaveTradeRetryLogic:
    """TEST_034_03_01 — save_trade com retry 3x e backoff."""

    async def test_save_trade_succeeds_on_first_attempt(self) -> None:
        """save_trade sem erros retorna doc_id na primeira tentativa."""
        real_repo = _make_real_repo()
        real_repo.save_trade = AsyncMock(return_value="doc_123")

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
        )

        trade = _make_trade()
        result = await resilient.save_trade(trade)

        assert result == "doc_123"
        assert real_repo.save_trade.call_count == 1

    async def test_save_trade_retries_on_temporary_failure(self) -> None:
        """save_trade retenta 3x em falhas temporárias."""
        real_repo = _make_real_repo()
        # Falha 2x, sucesso na 3ª
        real_repo.save_trade = AsyncMock(
            side_effect=[
                Exception("Network error"),
                Exception("Timeout"),
                "doc_456",
            ]
        )

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
        )

        trade = _make_trade()
        result = await resilient.save_trade(trade)

        assert result == "doc_456"
        assert real_repo.save_trade.call_count == 3

    async def test_save_trade_fails_after_3_retries(self) -> None:
        """save_trade retenta 3x e falha — não levanta exceção."""
        real_repo = _make_real_repo()
        real_repo.save_trade = AsyncMock(side_effect=Exception("MongoDB down"))

        notifier = _make_notifier()
        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=notifier,
        )

        trade = _make_trade()
        # Não deve levantar exceção
        result = await resilient.save_trade(trade)

        assert result is None
        assert real_repo.save_trade.call_count == 3
        # Deve ter enviado alert
        assert notifier.send.call_count == 1

    async def test_save_trade_with_backoff_delays(self) -> None:
        """save_trade aplica backoff: 100ms, 200ms, 400ms entre tentativas."""
        real_repo = _make_real_repo()

        # Rastreador de timing de chamadas
        call_times: list[float] = []

        async def tracked_save_trade(trade: Trade) -> str | None:
            call_times.append(time.time())
            raise Exception("MongoDB error")

        real_repo.save_trade = tracked_save_trade

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
        )

        trade = _make_trade()
        start_time = time.time()
        await resilient.save_trade(trade)

        # Validar que houve 3 chamadas
        assert len(call_times) == 3

        # Validar espaçamento: 1ª→2ª ≈ 100ms, 2ª→3ª ≈ 200ms
        if len(call_times) >= 2:
            delay_1 = call_times[1] - call_times[0]
            delay_2 = call_times[2] - call_times[1]
            # Backoff esperado: 100ms e 200ms (tolerância ±50ms)
            assert 0.05 < delay_1 < 0.15, f"1º backoff: {delay_1}s (expected ~0.1s)"
            assert 0.15 < delay_2 < 0.25, f"2º backoff: {delay_2}s (expected ~0.2s)"


@pytest.mark.asyncio
class TestSaveTradeJournaling:
    """TEST_034_03_02 — save_trade com falha 3x → PendingTradesJournal."""

    async def test_save_trade_journals_after_3_failures(self) -> None:
        """save_trade falha 3x e escreve em journal."""
        real_repo = _make_real_repo()
        real_repo.save_trade = AsyncMock(side_effect=Exception("MongoDB error"))

        journal = AsyncMock(spec=PendingTradesJournal)
        journal.add_trade = AsyncMock()

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
            journal=journal,
        )

        trade = _make_trade(entry_order_id="test_order_999")
        await resilient.save_trade(trade)

        # Journal deve ter sido chamado
        assert journal.add_trade.call_count == 1
        journal.add_trade.assert_called_with(trade)

    async def test_save_trade_returns_none_after_journaling(self) -> None:
        """save_trade com falha 3x retorna None (não exceção)."""
        real_repo = _make_real_repo()
        real_repo.save_trade = AsyncMock(side_effect=Exception("MongoDB error"))

        journal = AsyncMock(spec=PendingTradesJournal)
        journal.add_trade = AsyncMock()

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
            journal=journal,
        )

        trade = _make_trade()
        result = await resilient.save_trade(trade)

        assert result is None  # Não levanta exceção, retorna None

    async def test_save_trade_idempotent_journaling(self) -> None:
        """save_trade com CB aberto journala ao invés de retornar erro."""
        real_repo = _make_real_repo()
        journal = AsyncMock(spec=PendingTradesJournal)
        journal.add_trade = AsyncMock()

        cb_registry = CircuitBreakerRegistry(namespace="mongodb")
        # Força CB para OPEN
        cb = cb_registry.get("mongodb:save_trade", recovery_timeout=60)
        cb.state = CircuitBreakerState.OPEN

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
            cb_registry=cb_registry,
            journal=journal,
        )

        trade = _make_trade()
        result = await resilient.save_trade(trade)

        assert result is None
        # Com CB aberto, não tenta real_repo, vai direto ao journal
        assert real_repo.save_trade.call_count == 0
        assert journal.add_trade.call_count == 1


@pytest.mark.asyncio
class TestSaveSignalGracefulDegrade:
    """TEST_034_03_03 — save_signal com graceful degrade (Tipo C)."""

    async def test_save_signal_succeeds(self) -> None:
        """save_signal sem erros retorna doc_id."""
        real_repo = _make_real_repo()
        real_repo.save_signal = AsyncMock(return_value="signal_123")

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
        )

        signal_dict = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "direction": "long",
        }
        result = await resilient.save_signal(signal_dict)

        assert result == "signal_123"
        assert real_repo.save_signal.call_count == 1

    async def test_save_signal_returns_none_on_failure(self) -> None:
        """save_signal falha e retorna None (não retenta, graceful degrade)."""
        real_repo = _make_real_repo()
        real_repo.save_signal = AsyncMock(side_effect=Exception("MongoDB error"))

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
        )

        signal_dict = {"symbol": "BTCUSDT", "timeframe": "15m"}
        result = await resilient.save_signal(signal_dict)

        assert result is None
        # Tipo C: tenta apenas 1x, não retenta
        assert real_repo.save_signal.call_count == 1

    async def test_save_signal_with_open_cb_returns_none(self) -> None:
        """save_signal com CB aberto retorna None sem tomar ação."""
        real_repo = _make_real_repo()
        real_repo.save_signal = AsyncMock()

        cb_registry = CircuitBreakerRegistry(namespace="mongodb")
        cb = cb_registry.get("mongodb:save_signal", recovery_timeout=60)
        cb.state = CircuitBreakerState.OPEN

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
            cb_registry=cb_registry,
        )

        signal_dict = {"symbol": "BTCUSDT"}
        result = await resilient.save_signal(signal_dict)

        assert result is None
        # CB aberto: não tenta sequer uma vez
        assert real_repo.save_signal.call_count == 0


@pytest.mark.asyncio
class TestAuditLogRetry:
    """TEST_034_03_04 — audit_log com retry 3x (Tipo B)."""

    async def test_audit_log_succeeds(self) -> None:
        """audit_log sem erros persiste evento."""
        real_repo = _make_real_repo()
        real_repo.audit = AsyncMock()

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
        )

        event_data = {"trade_id": "123", "status": "opened"}
        await resilient.audit_log("trade_opened", event_data)

        assert real_repo.audit.call_count == 1
        real_repo.audit.assert_called_with("trade_opened", event_data)

    async def test_audit_log_retries_on_failure(self) -> None:
        """audit_log retenta 3x em falhas."""
        real_repo = _make_real_repo()
        real_repo.audit = AsyncMock(
            side_effect=[
                Exception("Network error"),
                Exception("Timeout"),
                None,  # 3ª tentativa: sucesso
            ]
        )

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
        )

        await resilient.audit_log("test_event", {})

        assert real_repo.audit.call_count == 3

    async def test_audit_log_sends_alert_after_3_failures(self) -> None:
        """audit_log falha 3x e envia Telegram alert."""
        real_repo = _make_real_repo()
        real_repo.audit = AsyncMock(side_effect=Exception("MongoDB error"))

        notifier = _make_notifier()
        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=notifier,
        )

        await resilient.audit_log("test_event", {})

        assert real_repo.audit.call_count == 3
        # Deve ter enviado alert após falha
        assert notifier.send.call_count == 1


@pytest.mark.asyncio
class TestInsertOne:
    """TEST_034_03_05 — insert_one genérico com retry 3x."""

    async def test_insert_one_succeeds(self) -> None:
        """insert_one sem erros retorna doc_id."""
        real_repo = _make_real_repo()
        real_repo.database = MagicMock()
        mock_collection = AsyncMock()
        mock_result = MagicMock()
        mock_result.inserted_id = "obj_456"
        mock_collection.insert_one = AsyncMock(return_value=mock_result)
        real_repo.database.__getitem__ = MagicMock(return_value=mock_collection)

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
        )

        doc = {"field": "value"}
        result = await resilient.insert_one("test_collection", doc)

        assert result == "obj_456"

    async def test_insert_one_retries_on_failure(self) -> None:
        """insert_one retenta 3x."""
        real_repo = _make_real_repo()
        real_repo.database = MagicMock()
        mock_collection = AsyncMock()
        # Falha 2x, sucesso na 3ª
        mock_collection.insert_one = AsyncMock(
            side_effect=[
                Exception("error1"),
                Exception("error2"),
                MagicMock(inserted_id="obj_789"),
            ]
        )
        real_repo.database.__getitem__ = MagicMock(return_value=mock_collection)

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
        )

        doc = {"field": "value"}
        result = await resilient.insert_one("test_collection", doc)

        assert result == "obj_789"
        assert mock_collection.insert_one.call_count == 3

    async def test_insert_one_returns_none_after_3_failures(self) -> None:
        """insert_one falha 3x e retorna None."""
        real_repo = _make_real_repo()
        real_repo.database = MagicMock()
        mock_collection = AsyncMock()
        mock_collection.insert_one = AsyncMock(side_effect=Exception("error"))
        real_repo.database.__getitem__ = MagicMock(return_value=mock_collection)

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
        )

        doc = {"field": "value"}
        result = await resilient.insert_one("test_collection", doc)

        assert result is None


@pytest.mark.asyncio
class TestCircuitBreakerIntegration:
    """TEST_034_03_06 — Integração com CircuitBreaker e recovery_timeout."""

    async def test_circuit_breaker_opens_after_failures(self) -> None:
        """CB abre após 3 falhas consecutivas."""
        real_repo = _make_real_repo()
        real_repo.save_trade = AsyncMock(side_effect=Exception("error"))

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
            recovery_timeout_secs=60,
        )

        trade = _make_trade()

        # Primeira chamada: falha 3x, CB abre
        await resilient.save_trade(trade)
        # Segunda chamada: CB já está aberto, não tenta
        await resilient.save_trade(trade)

        # Contagem: 3 do primeiro + 0 do segundo (CB aberto) = 3 total
        assert real_repo.save_trade.call_count == 3

    async def test_recovery_timeout_respected(self) -> None:
        """CB respeita recovery_timeout antes de tentar HALF_OPEN."""
        real_repo = _make_real_repo()
        real_repo.save_trade = AsyncMock(side_effect=Exception("error"))

        cb_registry = CircuitBreakerRegistry(namespace="mongodb")
        # Define timeout curto para teste
        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
            cb_registry=cb_registry,
            recovery_timeout_secs=1,  # 1 segundo
        )

        trade = _make_trade()

        # Primeira chamada: falha 3x, CB abre
        await resilient.save_trade(trade)
        assert real_repo.save_trade.call_count == 3

        # Aguarda recovery_timeout
        await asyncio.sleep(1.1)

        # Segunda chamada: CB tenta HALF_OPEN, falha novamente
        real_repo.save_trade.reset_mock()
        real_repo.save_trade.side_effect = Exception("still failing")
        await resilient.save_trade(trade)

        # Deve ter tentado novamente (HALF_OPEN)
        assert real_repo.save_trade.call_count == 3


@pytest.mark.asyncio
class TestPassthroughMethods:
    """TEST_034_03_07 — Métodos passthroughs sem resiliência."""

    async def test_passthrough_get_open_trades(self) -> None:
        """get_open_trades é delegado para real_repo."""
        real_repo = _make_real_repo()
        real_repo.get_open_trades = AsyncMock(return_value=[{"trade": 1}])

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
        )

        result = await resilient.get_open_trades()

        assert result == [{"trade": 1}]
        assert real_repo.get_open_trades.call_count == 1

    async def test_passthrough_count_open_trades(self) -> None:
        """count_open_trades é delegado para real_repo."""
        real_repo = _make_real_repo()
        real_repo.count_open_trades = AsyncMock(return_value=5)

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
        )

        result = await resilient.count_open_trades()

        assert result == 5

    async def test_passthrough_database_property(self) -> None:
        """database property expõe real_repo.database."""
        real_repo = _make_real_repo()
        mock_db = MagicMock()
        real_repo.database = mock_db

        resilient = ResilientMongoRepository(
            real_repo=real_repo,
            notifier=_make_notifier(),
        )

        assert resilient.database == mock_db
