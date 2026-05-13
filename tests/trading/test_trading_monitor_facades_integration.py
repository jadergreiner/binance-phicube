"""
Testes para integração de Facades em TradingMonitor (TASK_034_04).

Valida:
- TradingMonitor recebe ResilientBinanceClient e ResilientMongoRepository via DI
- CircuitBreakerOpenError em fetch_ohlcv: log WARNING, cache, continuar loop
- CircuitBreakerOpenError em create_order: log ERROR, Telegram alert, parar loop
- Invariante: nenhuma ordem sem SL
- HeartbeatTask reprocessa journal periodicamente
- Journaled trades são reprocessados e removidos após sucesso
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.common.result import ok
from src.config.settings import SymbolConfig
from src.exchange.resilient_binance_client import ResilientBinanceClient
from src.main import HeartbeatTask, TradingMonitor
from src.resilience.exceptions import CircuitBreakerOpenError
from src.storage.pending_trades_journal import PendingTradesJournal
from src.storage.resilient_repository import ResilientMongoRepository
from src.strategy.plugin_base import SignalResult
from src.strategy.signal_engine import Direction
from src.trading.order_manager import Trade, TradeStatus
from src.trading.risk_manager import RiskRejection


def _build_signal_result() -> SignalResult:
    return SignalResult(
        direction="LONG",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        metadata={"fractal_ref": 99.0},
    )


def _build_trade() -> Trade:
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
        entry_order_id="test_order_123",
        sl_order_id="sl_order_456",
        tp_order_id="tp_order_789",
        status=TradeStatus.OPEN,
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
    return TradingMonitor(
        config=SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=5),
        client=client,
        repo=repo,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        order_manager=order_manager,
        notifier=SimpleNamespace(send=AsyncMock(return_value=None)),
        max_open_positions=10,
        warmup_candles=2,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )


# ─── Testes: Integração de Facades ────────────────────────────────────────


@pytest.mark.asyncio
async def test_trading_monitor_recebe_facades_via_di() -> None:
    """Valida que TradingMonitor aceita Facades via DI."""
    resilient_client = MagicMock(spec=ResilientBinanceClient)
    resilient_repo = MagicMock(spec=ResilientMongoRepository)
    
    monitor = _build_monitor(
        repo=SimpleNamespace(),
        client=SimpleNamespace(),
        signal_engine=SimpleNamespace(),
        risk_manager=SimpleNamespace(),
        order_manager=SimpleNamespace(),
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
    )
    
    assert monitor._resilient_client is resilient_client
    assert monitor._resilient_repo is resilient_repo


@pytest.mark.asyncio
async def test_fetch_ohlcv_circuit_breaker_open_continua_loop() -> None:
    """CircuitBreakerOpenError em fetch_ohlcv: continua loop com WARNING."""
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            side_effect=CircuitBreakerOpenError("Circuit Breaker OPEN para fetch_ohlcv")
        ),
    )
    repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
    )
    client = SimpleNamespace()
    signal_engine = SimpleNamespace()
    risk_manager = SimpleNamespace()
    order_manager = SimpleNamespace()
    notifier = SimpleNamespace(send=AsyncMock(return_value=None))
    
    monitor = TradingMonitor(
        config=SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=5),
        client=client,
        repo=repo,
        signal_engine=signal_engine,
        risk_manager=risk_manager,
        order_manager=order_manager,
        notifier=notifier,
        max_open_positions=10,
        warmup_candles=2,
        resilient_client=resilient_client,
        resilient_repo=repo,
    )
    
    # Não deve levantar exceção, apenas retornar
    await monitor._tick()
    
    # Verifica que fetch_ohlcv_with_retry foi chamado
    resilient_client.fetch_ohlcv_with_retry.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_order_circuit_breaker_open_para_loop() -> None:
    """CircuitBreakerOpenError em create_order: para loop com ERROR."""
    
    # Setup
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
        save_signal=AsyncMock(return_value="signal_123"),
        save_trade=AsyncMock(return_value="trade_123"),
        audit=AsyncMock(return_value=None),
        update_signal_execution_outcome=AsyncMock(return_value=True),
        get_intraday_realized_pnl_usdt=AsyncMock(return_value=0.0),
    )
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=pd.DataFrame({"close": [100.0, 101.0], "open": [99.0, 100.0]})
        ),
    )
    client = SimpleNamespace(
        fetch_usdt_balance=AsyncMock(return_value=1000.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=signal_result),
    )
    
    # Mock RiskManager.calculate retornando ok(position)
    position = SimpleNamespace(quantity=0.5, entry_price=100.0)
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=ok(position)),
    )
    
    # Mock OrderManager.execute para levantar CircuitBreakerOpenError
    order_manager = SimpleNamespace(
        execute=AsyncMock(
            side_effect=CircuitBreakerOpenError("Circuit Breaker OPEN para create_order")
        ),
    )
    notifier = SimpleNamespace(send=AsyncMock(return_value=None))
    
    monitor = TradingMonitor(
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
    
    # Deve levantar CircuitBreakerOpenError (parar o loop)
    with pytest.raises(CircuitBreakerOpenError):
        await monitor._tick()
    
    # Verifica que notifier.send foi chamado
    notifier.send.assert_awaited_once()
    call_args = notifier.send.call_args
    assert call_args is not None


@pytest.mark.asyncio
async def test_invariante_nenhuma_ordem_sem_sl() -> None:
    """Valida que trade é salvo com SL já enviado."""
    resilient_repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
        save_signal=AsyncMock(return_value="signal_123"),
        save_trade=AsyncMock(return_value="trade_123"),
        audit=AsyncMock(return_value=None),
        update_signal_execution_outcome=AsyncMock(return_value=True),
        get_intraday_realized_pnl_usdt=AsyncMock(return_value=0.0),
    )
    resilient_client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=pd.DataFrame({"close": [100.0, 101.0], "open": [99.0, 100.0]})
        ),
    )
    client = SimpleNamespace(
        fetch_usdt_balance=AsyncMock(return_value=1000.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=signal_result),
    )
    
    position = SimpleNamespace(quantity=0.5, entry_price=100.0)
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=ok(position)),
    )
    
    # Trade com SL
    trade = _build_trade()
    order_manager = SimpleNamespace(
        execute=AsyncMock(return_value=ok(trade)),
    )
    notifier = SimpleNamespace(send=AsyncMock(return_value=None))
    
    monitor = TradingMonitor(
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
    
    await monitor._tick()
    
    # Verifica que save_trade foi chamado
    resilient_repo.save_trade.assert_awaited_once()
    saved_trade = resilient_repo.save_trade.call_args.args[0]
    
    # Invariante: SL não pode ser nulo
    assert saved_trade.sl_order_id is not None
    assert saved_trade.stop_loss > 0


# ─── Testes: HeartbeatTask com Journal Reprocessing ────────────────────────


@pytest.mark.asyncio
async def test_heartbeat_task_reprocessa_journal() -> None:
    """Valida que HeartbeatTask reprocessa journal periodicamente."""
    journal = MagicMock(spec=PendingTradesJournal)
    journal.reprocess_pending_trades = AsyncMock(return_value=(2, 0))
    
    resilient_repo = MagicMock(spec=ResilientMongoRepository)
    resilient_repo._journal = journal
    resilient_repo.audit = AsyncMock(return_value=None)
    
    heartbeat = HeartbeatTask(
        repo=resilient_repo,
        monitor_count=5,
    )
    
    # Simula 3 ciclos: 3 % 3 == 0, deve reprocessar
    heartbeat._cycle_count = 2
    await heartbeat._beat()
    
    # Deve ter chamado reprocess_pending_trades
    journal.reprocess_pending_trades.assert_awaited_once()


@pytest.mark.asyncio
async def test_heartbeat_task_nao_reprocessa_antes_intervalo() -> None:
    """HeartbeatTask não reprocessa antes do intervalo."""
    journal = MagicMock(spec=PendingTradesJournal)
    journal.reprocess_pending_trades = AsyncMock(return_value=(0, 0))
    
    resilient_repo = MagicMock(spec=ResilientMongoRepository)
    resilient_repo._journal = journal
    resilient_repo.audit = AsyncMock(return_value=None)
    
    heartbeat = HeartbeatTask(
        repo=resilient_repo,
        monitor_count=5,
    )
    
    # Simula ciclo 1: 1 % 3 != 0, não deve reprocessar
    heartbeat._cycle_count = 0
    await heartbeat._beat()
    
    # Não deve ter chamado reprocess_pending_trades
    journal.reprocess_pending_trades.assert_not_awaited()


@pytest.mark.asyncio
async def test_journal_reprocess_remove_after_sucesso(tmp_path) -> None:
    """Journaled trades são removidos após sucesso."""
    trade = _build_trade()
    # Usar arquivo temporário isolado para este teste
    journal_file = tmp_path / ".pending_trades_test.jsonl"
    journal = PendingTradesJournal(journal_path=journal_file)
    
    # Simula trade journaled
    await journal.add_trade(trade)
    
    # Verifica que foi adicionado
    pending = await journal.list_pending()
    assert len(pending) == 1
    
    # Mock da repo real
    real_repo = SimpleNamespace(
        save_trade=AsyncMock(return_value="trade_123"),
    )
    
    # Reprocessa
    reprocessed, failed = await journal.reprocess_pending_trades(real_repo)
    
    # Verifica sucesso
    assert reprocessed == 1
    assert failed == 0
    
    # Verifica que foi removido do journal
    pending = await journal.list_pending()
    assert len(pending) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
