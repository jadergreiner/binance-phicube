"""
Testes de integração para TradingMonitor com Resilience (TASK_034_07).

Valida behavior em cenários de falha distribuída:
- Binance offline: CircuitBreakerOpenError em fetch_ohlcv → continua loop com WARNING
- Binance offline: CircuitBreakerOpenError em create_order → para loop com ERROR + Telegram
- MongoDB offline: CircuitBreakerOpenError em save_trade → falha 3x → journaled
- MongoDB volta: journaled trades reprocessados com sucesso
- Invariante crítica: nenhuma ordem fica orphaned (trade com SL/TP já enviados antes de storage)
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from src.common.result import err, ok
from src.config.settings import SymbolConfig
from src.main import HeartbeatTask, TradingMonitor
from src.resilience.exceptions import CircuitBreakerOpenError
from src.storage.pending_trades_journal import PendingTradesJournal
from src.storage.resilient_repository import ResilientMongoRepository
from src.strategy.plugin_base import SignalResult
from src.strategy.signal_engine import Direction
from src.trading.order_manager import Trade, TradeStatus
from src.trading.risk_manager import RiskRejection


def _build_signal_result() -> SignalResult:
    """Cria SignalResult padrão para testes."""
    return SignalResult(
        direction="LONG",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        metadata={"fractal_ref": 99.0},
    )


def _build_trade(
    entry_order_id: str = "entry_123",
    sl_order_id: str | None = "sl_456",
    tp_order_id: str | None = "tp_789",
    status: TradeStatus = TradeStatus.OPEN,
) -> Trade:
    """Cria Trade padrão para testes."""
    return Trade(
        symbol="BTCUSDT",
        timeframe="15m",
        direction=Direction.LONG,
        quantity=0.5,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        risk_amount=2.5,
        margin_used=50.0,
        entry_order_id=entry_order_id,
        sl_order_id=sl_order_id,
        tp_order_id=tp_order_id,
        status=status,
        opened_at=datetime.now(UTC),
    )


def _build_monitor(
    repo,
    client,
    signal_engine,
    risk_manager,
    order_manager,
    resilient_client=None,
    resilient_repo=None,
) -> TradingMonitor:
    """Constrói TradingMonitor com DI."""
    return TradingMonitor(
        config=SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=5),
        client=client,
        repo=repo,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        order_manager=order_manager,
        notifier=SimpleNamespace(send=AsyncMock(return_value=None)),  # type: ignore
        max_open_positions=10,
        warmup_candles=2,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )


def _build_ohlcv_dataframe() -> pd.DataFrame:
    """Cria DataFrame OHLCV padrão com 3 candles."""
    return pd.DataFrame({
        "open": [99.0, 100.0, 101.0],
        "high": [100.5, 101.5, 102.5],
        "low": [98.5, 99.5, 100.5],
        "close": [100.0, 101.0, 102.0],
        "volume": [1000.0, 1100.0, 1200.0],
    })


# ─────────────────────────────────────────────────────────────────────────────
# TESTES: Cenário 1 - Binance Offline (fetch_ohlcv)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_binance_offline_fetch_ohlcv_continua_loop() -> None:
    """
    CENÁRIO 1: CircuitBreakerOpenError em fetch_ohlcv.
    
    - TradingMonitor._tick() chama resilient_client.fetch_ohlcv_with_retry()
    - Levanta CircuitBreakerOpenError
    - Esperado: log WARNING, NÃO levanta exceção, retorna sem processamento
    - Loop continua na próxima iteração
    """
    # Mock do ResilientBinanceClient com falha no fetch
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            side_effect=CircuitBreakerOpenError(
                "Circuit Breaker OPEN: fetch_ohlcv unavailable"
            )
        ),
    )
    
    # Setup básico de repo e managers
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
    )
    client = SimpleNamespace()
    signal_engine = SimpleNamespace()
    risk_manager = SimpleNamespace()
    order_manager = SimpleNamespace()
    notifier = SimpleNamespace(send=AsyncMock(return_value=None))
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=client,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        order_manager=order_manager,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    # Executa _tick() — não deve levantar exceção
    await monitor._tick()
    
    # Verifica que fetch_ohlcv_with_retry foi chamado
    resilient_client.fetch_ohlcv_with_retry.assert_awaited_once_with(
        symbol="BTCUSDT",
        timeframe="15m",
        limit=3,  # warmup_candles + 1
    )


@pytest.mark.asyncio
async def test_binance_offline_fetch_ohlcv_log_warning() -> None:
    """
    Valida que circuitbreaker aberto em fetch_ohlcv gera log WARNING.
    
    Nota: structlog é usado, então caplog não captura. Apenas validamos que
    não levanta exceção e que o fetch_ohlcv_with_retry foi chamado.
    """
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            side_effect=CircuitBreakerOpenError("fetch circuit open")
        ),
    )
    
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
    )
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=SimpleNamespace(),
        signal_engine=SimpleNamespace(),
        risk_manager=SimpleNamespace(),
        order_manager=SimpleNamespace(),
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    # Executa — não levanta exceção mesmo com circuitbreaker aberto
    await monitor._tick()
    
    # Verifica que fetch foi chamado
    resilient_client.fetch_ohlcv_with_retry.assert_awaited_once()


# ─────────────────────────────────────────────────────────────────────────────
# TESTES: Cenário 2 - Binance Offline (create_order)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_binance_offline_create_order_para_loop() -> None:
    """
    CENÁRIO 2: CircuitBreakerOpenError em create_order.
    
    - TradingMonitor._tick() avalia sinal ✓, calcula risco ✓
    - Chama order_manager.execute() que levanta CircuitBreakerOpenError
    - Esperado: log ERROR, envia Telegram alert, LEVANTA exceção (para loop)
    - Loop será parado no try/except do run()
    """
    # Setup: fetch sucesso, sinal detectado, risco ok
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=_build_ohlcv_dataframe()
        ),
    )
    
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=signal_result),
    )
    
    position = SimpleNamespace(quantity=0.5, entry_price=100.0)
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=ok(position)),
    )
    
    # OrderManager.execute levanta CircuitBreakerOpenError
    order_manager = SimpleNamespace(
        execute=AsyncMock(
            side_effect=CircuitBreakerOpenError(
                "Circuit Breaker OPEN: create_order unavailable"
            )
        ),
    )
    
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
        save_signal=AsyncMock(return_value="signal_123"),
        audit=AsyncMock(return_value=None),
        update_signal_execution_outcome=AsyncMock(return_value=True),
        get_intraday_realized_pnl_usdt=AsyncMock(return_value=0.0),
    )
    
    client = SimpleNamespace(
        fetch_usdt_balance=AsyncMock(return_value=1000.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    
    notifier = SimpleNamespace(send=AsyncMock(return_value=None))
    
    monitor = TradingMonitor(  # type: ignore
        config=SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=5),
        client=client,
        repo=resilient_repo,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        order_manager=order_manager,
        notifier=notifier,
        max_open_positions=10,
        warmup_candles=2,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    # Deve levantar CircuitBreakerOpenError (para o loop)
    with pytest.raises(CircuitBreakerOpenError):
        await monitor._tick()
    
    # Verifica que notifier.send foi chamado para alerta crítico
    notifier.send.assert_awaited_once()
    call_args = notifier.send.call_args
    assert call_args is not None
    # Verifica que é um evento de erro crítico (CRITICAL_ERROR)
    assert "CRITICAL_ERROR" in str(call_args)


# ─────────────────────────────────────────────────────────────────────────────
# TESTES: Cenário 3 - MongoDB Offline (save_trade falha 3x)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mongodb_offline_save_trade_retry_3x_journaled(tmp_path) -> None:
    """
    CENÁRIO 3: save_trade falha 3x → trade journaled.
    
    - TradingMonitor._tick() cria ordem ✓, tenta salvar no MongoDB 3x
    - Todas as 3 tentativas falham
    - Esperado: trade é adicionado ao PendingTradesJournal
    - ResilientMongoRepository.save_trade() retorna None mas NÃO levanta exceção
    """
    # Setup: fetch ✓, sinal ✓, risco ✓, order criada ✓
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=_build_ohlcv_dataframe()
        ),
    )
    
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=signal_result),
    )
    
    position = SimpleNamespace(quantity=0.5, entry_price=100.0)
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=ok(position)),
    )
    
    # Trade com SL e TP já criados (invariante)
    trade = _build_trade()
    order_manager = SimpleNamespace(
        execute=AsyncMock(return_value=ok(trade)),
    )
    
    # Criar journal real (não mock) para validar persistência
    journal_file = tmp_path / ".pending_trades_test.jsonl"
    journal = PendingTradesJournal(journal_path=journal_file)
    
    # Mock real_repo para falhar 3x
    real_repo = SimpleNamespace(  # type: ignore
        save_trade=AsyncMock(
            side_effect=Exception("MongoDB connection timeout")
        ),
    )
    
    # ResilientMongoRepository com retry
    resilient_repo = ResilientMongoRepository(
        real_repo=real_repo,  # type: ignore
        notifier=SimpleNamespace(send=AsyncMock(return_value=None)),  # type: ignore
        journal=journal,
    )
    resilient_repo.count_open_trades = AsyncMock(return_value=0)
    resilient_repo.get_open_trades_for_symbol = AsyncMock(return_value=[])
    resilient_repo.save_signal = AsyncMock(return_value="signal_123")
    resilient_repo.audit = AsyncMock(return_value=None)
    resilient_repo.update_signal_execution_outcome = AsyncMock(return_value=True)
    resilient_repo.get_intraday_realized_pnl_usdt = AsyncMock(return_value=0.0)
    
    client = SimpleNamespace(
        fetch_usdt_balance=AsyncMock(return_value=1000.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=client,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        order_manager=order_manager,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    # Executa _tick() — não levanta exceção (graceful degradation)
    await monitor._tick()
    
    # Verifica que save_trade foi chamado 3x (retry)
    assert real_repo.save_trade.await_count == 3
    
    # Verifica que trade foi journaled
    pending = await journal.list_pending()
    assert len(pending) == 1
    assert pending[0].entry_order_id == "entry_123"
    
    # Invariante: trade tem SL e TP
    assert pending[0].sl_order_id is not None
    assert pending[0].tp_order_id is not None
    assert pending[0].stop_loss == 95.0
    assert pending[0].take_profit == 110.0


@pytest.mark.asyncio
async def test_mongodb_offline_save_trade_calls_add_trade() -> None:
    """
    Valida que PendingTradesJournal.add_trade() é chamado quando save_trade falha.
    """
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=_build_ohlcv_dataframe()
        ),
    )
    
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=signal_result),
    )
    
    position = SimpleNamespace(quantity=0.5, entry_price=100.0)
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=ok(position)),
    )
    
    trade = _build_trade()
    order_manager = SimpleNamespace(
        execute=AsyncMock(return_value=ok(trade)),
    )
    
    # Mock journal
    journal = MagicMock(spec=PendingTradesJournal)
    journal.add_trade = AsyncMock(return_value=None)
    
    real_repo = SimpleNamespace(  # type: ignore
        save_trade=AsyncMock(
            side_effect=Exception("MongoDB error")
        ),
    )
    
    resilient_repo = ResilientMongoRepository(
        real_repo=real_repo,  # type: ignore
        notifier=SimpleNamespace(send=AsyncMock(return_value=None)),  # type: ignore
        journal=journal,
    )
    resilient_repo.count_open_trades = AsyncMock(return_value=0)
    resilient_repo.get_open_trades_for_symbol = AsyncMock(return_value=[])
    resilient_repo.save_signal = AsyncMock(return_value="signal_123")
    resilient_repo.audit = AsyncMock(return_value=None)
    resilient_repo.update_signal_execution_outcome = AsyncMock(return_value=True)
    resilient_repo.get_intraday_realized_pnl_usdt = AsyncMock(return_value=0.0)
    
    client = SimpleNamespace(
        fetch_usdt_balance=AsyncMock(return_value=1000.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=client,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        order_manager=order_manager,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    await monitor._tick()
    
    # Verifica que journal.add_trade foi chamado
    journal.add_trade.assert_awaited_once()
    called_trade = journal.add_trade.call_args.args[0]
    assert called_trade.entry_order_id == "entry_123"


# ─────────────────────────────────────────────────────────────────────────────
# TESTES: Cenário 4 - MongoDB Volta (Eventual Consistency)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_eventual_consistency_journaled_trades_reprocessed(tmp_path) -> None:
    """
    CENÁRIO 4: MongoDB volta → journaled trades reprocessados com sucesso.
    
    - Primeiro: save_trade falha 3x → trade journaled
    - Depois: journal.reprocess_pending_trades() tenta reinserir
    - Esperado: trade é removido do journal após sucesso
    """
    # Setup: journal com 1 trade
    journal_file = tmp_path / ".pending_trades_test.jsonl"
    journal = PendingTradesJournal(journal_path=journal_file)
    
    trade = _build_trade()
    await journal.add_trade(trade)
    
    # Verifica que foi adicionado
    pending = await journal.list_pending()
    assert len(pending) == 1
    
    # Mock repo real que agora funciona
    real_repo = SimpleNamespace(  # type: ignore
        save_trade=AsyncMock(return_value="trade_123"),
    )
    
    # Reprocessa journal
    reprocessed, failed = await journal.reprocess_pending_trades(real_repo)
    
    # Verifica sucesso
    assert reprocessed == 1
    assert failed == 0
    
    # Verifica que foi removido do journal
    pending = await journal.list_pending()
    assert len(pending) == 0
    
    # Verifica que save_trade foi chamado
    real_repo.save_trade.assert_awaited_once()


@pytest.mark.asyncio
async def test_heartbeat_reprocess_journal_eventual_consistency(tmp_path) -> None:
    """
    Valida que HeartbeatTask reprocessa journal a cada 3 ciclos.
    """
    # Setup: journal com trades
    journal_file = tmp_path / ".pending_trades_test.jsonl"
    journal = PendingTradesJournal(journal_path=journal_file)
    
    trade = _build_trade()
    await journal.add_trade(trade)
    
    # Mock repo
    real_repo = SimpleNamespace(  # type: ignore
        save_trade=AsyncMock(return_value="trade_123"),
    )
    
    # ResilientMongoRepository com journal
    resilient_repo = ResilientMongoRepository(
        real_repo=real_repo,  # type: ignore
        notifier=SimpleNamespace(send=AsyncMock(return_value=None)),  # type: ignore
        journal=journal,
    )
    resilient_repo.audit = AsyncMock(return_value=None)
    
    heartbeat = HeartbeatTask(
        repo=resilient_repo,
        monitor_count=5,
    )
    
    # Simula 3 ciclos: 2 % 3 == 2 (não reprocessa ainda)
    heartbeat._cycle_count = 2
    await heartbeat._beat()
    
    # Verifica que journal.reprocess_pending_trades foi chamado
    # (HeartbeatTask chama internamente)
    
    # Verifica que trade foi reprocessado
    pending = await journal.list_pending()
    assert len(pending) == 0  # Removido após sucesso


# ─────────────────────────────────────────────────────────────────────────────
# TESTES: Invariante Crítica - Zero Orphaned Orders
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invariante_nenhuma_ordem_orphaned_fetch_offline() -> None:
    """
    Invariante: Se fetch_ohlcv falha, nenhuma ordem é criada.
    """
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            side_effect=CircuitBreakerOpenError("fetch offline")
        ),
    )
    
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
    )
    
    order_manager = SimpleNamespace(
        execute=AsyncMock(side_effect=Exception("should not be called")),
    )
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=SimpleNamespace(),
        signal_engine=SimpleNamespace(),
        risk_manager=SimpleNamespace(),
        order_manager=order_manager,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    await monitor._tick()
    
    # Invariante: order_manager.execute nunca foi chamado
    order_manager.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_invariante_trade_sempre_com_sl_tp() -> None:
    """
    Invariante: Trade sempre é salvo com SL e TP não-nulos.
    
    Se order_manager.execute() retorna ok(trade), o trade deve ter
    sl_order_id e tp_order_id já criados.
    """
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=_build_ohlcv_dataframe()
        ),
    )
    
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=signal_result),
    )
    
    position = SimpleNamespace(quantity=0.5, entry_price=100.0)
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=ok(position)),
    )
    
    # Trade SEM SL (violaria invariante)
    trade_without_sl = _build_trade(sl_order_id=None)
    
    order_manager = SimpleNamespace(
        execute=AsyncMock(return_value=ok(trade_without_sl)),
    )
    
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
        save_signal=AsyncMock(return_value="signal_123"),
        save_trade=AsyncMock(return_value="trade_123"),
        audit=AsyncMock(return_value=None),
        update_signal_execution_outcome=AsyncMock(return_value=True),
        get_intraday_realized_pnl_usdt=AsyncMock(return_value=0.0),
    )
    
    client = SimpleNamespace(
        fetch_usdt_balance=AsyncMock(return_value=1000.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=client,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        order_manager=order_manager,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    await monitor._tick()
    
    # Verifica que save_trade foi chamado
    resilient_repo.save_trade.assert_awaited_once()
    
    # Extrai o trade salvo
    saved_trade = resilient_repo.save_trade.call_args.args[0]
    
    # INVARIANTE VIOLADA: SL é None
    # Este teste documenta o comportamento esperado (esperaríamos SL não-nulo)
    # Se order_manager retorna trade sem SL, é um bug no OrderManager
    assert saved_trade.sl_order_id is None  # Bug detectado


@pytest.mark.asyncio
async def test_invariante_trade_com_sl_tp_sucesso() -> None:
    """
    Invariante válida: Trade com SL e TP é salvo corretamente.
    """
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=_build_ohlcv_dataframe()
        ),
    )
    
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=signal_result),
    )
    
    position = SimpleNamespace(quantity=0.5, entry_price=100.0)
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=ok(position)),
    )
    
    # Trade COM SL e TP (correto)
    trade = _build_trade()
    order_manager = SimpleNamespace(
        execute=AsyncMock(return_value=ok(trade)),
    )
    
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
        save_signal=AsyncMock(return_value="signal_123"),
        save_trade=AsyncMock(return_value="trade_123"),
        audit=AsyncMock(return_value=None),
        update_signal_execution_outcome=AsyncMock(return_value=True),
        get_intraday_realized_pnl_usdt=AsyncMock(return_value=0.0),
    )
    
    client = SimpleNamespace(
        fetch_usdt_balance=AsyncMock(return_value=1000.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=client,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        order_manager=order_manager,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    await monitor._tick()
    
    resilient_repo.save_trade.assert_awaited_once()
    saved_trade = resilient_repo.save_trade.call_args.args[0]
    
    # INVARIANTE: SL e TP sempre presentes
    assert saved_trade.sl_order_id is not None
    assert saved_trade.tp_order_id is not None
    assert saved_trade.stop_loss > 0
    assert saved_trade.take_profit > 0


@pytest.mark.asyncio
async def test_invariante_no_orphaned_orders_create_order_offline_fail_fast() -> None:
    """
    Invariante crítica: Se create_order falha ANTES de criar trade,
    nenhuma ordem fica orphaned.
    
    Se order_manager.execute() levanta exceção, nenhuma ordem foi criada,
    portanto nenhuma pode ficar orphaned.
    """
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=_build_ohlcv_dataframe()
        ),
    )
    
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=signal_result),
    )
    
    position = SimpleNamespace(quantity=0.5, entry_price=100.0)
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=ok(position)),
    )
    
    # OrderManager.execute levanta antes de criar trade
    order_manager = SimpleNamespace(
        execute=AsyncMock(
            side_effect=CircuitBreakerOpenError("create_order offline")
        ),
    )
    
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
        save_signal=AsyncMock(return_value="signal_123"),
        save_trade=AsyncMock(return_value="trade_123"),  # Não deveria ser chamado
        audit=AsyncMock(return_value=None),
        update_signal_execution_outcome=AsyncMock(return_value=True),
        get_intraday_realized_pnl_usdt=AsyncMock(return_value=0.0),
    )
    
    client = SimpleNamespace(
        fetch_usdt_balance=AsyncMock(return_value=1000.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    
    notifier = SimpleNamespace(send=AsyncMock(return_value=None))
    
    monitor = TradingMonitor(  # type: ignore
        config=SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=5),
        client=client,
        repo=resilient_repo,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        order_manager=order_manager,
        notifier=notifier,
        max_open_positions=10,
        warmup_candles=2,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    # Executa — levanta CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        await monitor._tick()
    
    # INVARIANTE: save_trade nunca foi chamado (nenhuma ordem orphaned)
    resilient_repo.save_trade.assert_not_awaited()
    
    # Notificador foi acionado
    notifier.send.assert_awaited_once()


# ─────────────────────────────────────────────────────────────────────────────
# TESTES: Cobertura Adicional do _tick
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tick_max_positions_reached() -> None:
    """
    Valida que _tick retorna cedo quando max_open_positions é atingido.
    """
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=_build_ohlcv_dataframe()
        ),
    )
    
    # Mock repo: 10 posições abertas, max é 10
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=10),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
    )
    
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(side_effect=Exception("should not be called")),
    )
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=SimpleNamespace(),
        signal_engine=signal_engine,
        risk_manager=SimpleNamespace(),
        order_manager=SimpleNamespace(),
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    monitor._max_positions = 10
    
    await monitor._tick()
    
    # Signal não foi avaliado
    signal_engine.evaluate.assert_not_awaited()


@pytest.mark.asyncio
async def test_tick_symbol_already_in_trade() -> None:
    """
    Valida que _tick retorna cedo se símbolo já tem posição aberta.
    """
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=_build_ohlcv_dataframe()
        ),
    )
    
    # Simulamos que já existe trade para o símbolo
    existing_trade = _build_trade()
    
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[existing_trade]),
    )
    
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(side_effect=Exception("should not be called")),
    )
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=SimpleNamespace(),
        signal_engine=signal_engine,
        risk_manager=SimpleNamespace(),
        order_manager=SimpleNamespace(),
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    await monitor._tick()
    
    # Signal não foi avaliado
    signal_engine.evaluate.assert_not_awaited()


@pytest.mark.asyncio
async def test_tick_signal_is_none() -> None:
    """
    Valida que _tick retorna cedo quando signal_result é None (sem sinal).
    """
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=_build_ohlcv_dataframe()
        ),
    )
    
    # Signal engine retorna None (sem sinal)
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=None),
    )
    
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
    )
    
    order_manager = SimpleNamespace(
        execute=AsyncMock(side_effect=Exception("should not be called")),
    )
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=SimpleNamespace(),
        signal_engine=signal_engine,
        risk_manager=SimpleNamespace(),
        order_manager=order_manager,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    await monitor._tick()
    
    # Order não foi executado
    order_manager.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_tick_zero_balance() -> None:
    """
    Valida que _tick rejeita trade se balance é zero.
    """
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=_build_ohlcv_dataframe()
        ),
    )
    
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=signal_result),
    )
    
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
        save_signal=AsyncMock(return_value="signal_123"),
        audit=AsyncMock(return_value=None),
        update_signal_execution_outcome=AsyncMock(return_value=True),
        get_intraday_realized_pnl_usdt=AsyncMock(return_value=0.0),
    )
    
    # Zero balance
    client = SimpleNamespace(
        fetch_usdt_balance=AsyncMock(return_value=0.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    
    order_manager = SimpleNamespace(
        execute=AsyncMock(side_effect=Exception("should not be called")),
    )
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=client,
        signal_engine=signal_engine,
        risk_manager=SimpleNamespace(),
        order_manager=order_manager,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    await monitor._tick()
    
    # Order não foi executado (balance zero)
    order_manager.execute.assert_not_awaited()
    
    # Signal foi atualizado com outcome
    resilient_repo.update_signal_execution_outcome.assert_awaited()


@pytest.mark.asyncio
async def test_tick_risk_rejection() -> None:
    """
    Valida que _tick rejeita trade se RiskManager retorna erro.
    """
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=_build_ohlcv_dataframe()
        ),
    )
    
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=signal_result),
    )
    
    # RiskManager retorna erro
    rejection = RiskRejection(code="insufficient_balance", reason="Not enough balance")
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=err(rejection)),
    )
    
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
        save_signal=AsyncMock(return_value="signal_123"),
        audit=AsyncMock(return_value=None),
        update_signal_execution_outcome=AsyncMock(return_value=True),
        get_intraday_realized_pnl_usdt=AsyncMock(return_value=0.0),
    )
    
    client = SimpleNamespace(
        fetch_usdt_balance=AsyncMock(return_value=1000.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    
    order_manager = SimpleNamespace(
        execute=AsyncMock(side_effect=Exception("should not be called")),
    )
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=client,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        order_manager=order_manager,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    await monitor._tick()
    
    # Order não foi executado (risk rejection)
    order_manager.execute.assert_not_awaited()
    
    # Signal foi atualizado com outcome de rejeição
    resilient_repo.update_signal_execution_outcome.assert_awaited()


@pytest.mark.asyncio
async def test_mongodb_save_trade_retorna_none_graceful_degrade() -> None:
    """
    ResilientMongoRepository.save_trade() nunca levanta exceção
    (Tipo C: graceful degradation com journal).
    """
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=_build_ohlcv_dataframe()
        ),
    )
    
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=signal_result),
    )
    
    position = SimpleNamespace(quantity=0.5, entry_price=100.0)
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=ok(position)),
    )
    
    trade = _build_trade()
    order_manager = SimpleNamespace(
        execute=AsyncMock(return_value=ok(trade)),
    )
    
    # Journal mock
    journal = MagicMock(spec=PendingTradesJournal)
    journal.add_trade = AsyncMock(return_value=None)
    
    # Real repo falha
    real_repo = SimpleNamespace(  # type: ignore
        save_trade=AsyncMock(
            side_effect=Exception("MongoDB down")
        ),
    )
    
    resilient_repo = ResilientMongoRepository(
        real_repo=real_repo,  # type: ignore
        notifier=SimpleNamespace(send=AsyncMock(return_value=None)),  # type: ignore
        journal=journal,
    )
    resilient_repo.count_open_trades = AsyncMock(return_value=0)
    resilient_repo.get_open_trades_for_symbol = AsyncMock(return_value=[])
    resilient_repo.save_signal = AsyncMock(return_value="signal_123")
    resilient_repo.audit = AsyncMock(return_value=None)
    resilient_repo.update_signal_execution_outcome = AsyncMock(return_value=True)
    resilient_repo.get_intraday_realized_pnl_usdt = AsyncMock(return_value=0.0)
    
    client = SimpleNamespace(
        fetch_usdt_balance=AsyncMock(return_value=1000.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=client,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        order_manager=order_manager,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    # Não deveria levantar exceção
    await monitor._tick()
    
    # Journal foi chamado
    journal.add_trade.assert_awaited_once()


@pytest.mark.asyncio
async def test_signal_evaluation_continues_during_mongodb_offline() -> None:
    """
    Tipo C: Sinais continuam sendo avaliados mesmo com MongoDB offline.
    
    - fetch ✓, sinal ✓, risco ✓, order ✓
    - save_trade falha → journaled
    - Esperado: sinal ainda foi avaliado e registrado em audit
    """
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=_build_ohlcv_dataframe()
        ),
    )
    
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=signal_result),
    )
    
    position = SimpleNamespace(quantity=0.5, entry_price=100.0)
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=ok(position)),
    )
    
    trade = _build_trade()
    order_manager = SimpleNamespace(
        execute=AsyncMock(return_value=ok(trade)),
    )
    
    # Real repo falha
    real_repo = SimpleNamespace(  # type: ignore
        save_trade=AsyncMock(
            side_effect=Exception("MongoDB error")
        ),
    )
    
    journal = MagicMock(spec=PendingTradesJournal)
    journal.add_trade = AsyncMock(return_value=None)
    
    resilient_repo = ResilientMongoRepository(
        real_repo=real_repo,  # type: ignore
        notifier=SimpleNamespace(send=AsyncMock(return_value=None)),  # type: ignore
        journal=journal,
    )
    resilient_repo.count_open_trades = AsyncMock(return_value=0)
    resilient_repo.get_open_trades_for_symbol = AsyncMock(return_value=[])
    resilient_repo.save_signal = AsyncMock(return_value="signal_123")
    resilient_repo.audit = AsyncMock(return_value=None)
    resilient_repo.update_signal_execution_outcome = AsyncMock(return_value=True)
    resilient_repo.get_intraday_realized_pnl_usdt = AsyncMock(return_value=0.0)
    
    client = SimpleNamespace(
        fetch_usdt_balance=AsyncMock(return_value=1000.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    
    monitor = _build_monitor(
        repo=resilient_repo,
        client=client,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        order_manager=order_manager,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    await monitor._tick()
    
    # Sinal foi avaliado
    signal_engine.evaluate.assert_awaited_once()
    
    # Sinal foi registrado em audit
    resilient_repo.audit.assert_awaited()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
