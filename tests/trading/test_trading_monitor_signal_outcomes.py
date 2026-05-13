from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from src.config.settings import SymbolConfig
from src.main import TradingMonitor
from src.strategy.plugin_base import NullSignalResult, SignalResult
from src.strategy.signal_engine import Direction
from src.trading.order_manager import TradeStatus
from src.trading.risk_manager import RiskRejection


def _build_signal_result() -> SignalResult:
    return SignalResult(
        direction="LONG",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        metadata={"fractal_ref": 99.0},
    )


def _build_monitor(repo, client, signal_engine, risk_manager, order_manager) -> TradingMonitor:
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
    )


@pytest.mark.asyncio
async def test_tick_registra_desfecho_rejeicao_risco() -> None:
    repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
        get_intraday_realized_pnl_usdt=AsyncMock(return_value=0.0),
        save_signal=AsyncMock(return_value="681cc200e8f9ff89bff8e463"),
        audit=AsyncMock(return_value=None),
        update_signal_execution_outcome=AsyncMock(return_value=True),
    )
    client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=pd.DataFrame({"close": [100.0, 101.0], "open": [99.0, 100.0]})
        ),
        fetch_usdt_balance=AsyncMock(return_value=100.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(evaluate=AsyncMock(return_value=signal_result))
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=None),
        consume_last_rejection=lambda: RiskRejection(
            code="MAX_CAPITAL_ALLOCATION_EXCEEDED",
            reason="max_capital_allocation_exceeded",
            details={"margin_required": 10.0, "max_allowed_margin": 5.0},
        ),
    )
    order_manager = SimpleNamespace(execute=AsyncMock(return_value=None))

    monitor = _build_monitor(repo, client, signal_engine, risk_manager, order_manager)
    await monitor._tick()

    repo.update_signal_execution_outcome.assert_awaited_once()
    kwargs = repo.update_signal_execution_outcome.call_args.kwargs
    assert kwargs["execution_status"] == "REJECTED_RISK_MAX_CAPITAL"
    assert kwargs["execution_reason"] == "max_capital_allocation_exceeded"


@pytest.mark.asyncio
async def test_tick_registra_desfecho_rejeicao_intraday_loss_limit() -> None:
    repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
        get_intraday_realized_pnl_usdt=AsyncMock(return_value=-120.0),
        save_signal=AsyncMock(return_value="681cc200e8f9ff89bff8e463"),
        audit=AsyncMock(return_value=None),
        update_signal_execution_outcome=AsyncMock(return_value=True),
    )
    client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=pd.DataFrame({"close": [100.0, 101.0], "open": [99.0, 100.0]})
        ),
        fetch_usdt_balance=AsyncMock(return_value=1000.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(evaluate=AsyncMock(return_value=signal_result))
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=None),
        consume_last_rejection=lambda: RiskRejection(
            code="INTRADAY_LOSS_LIMIT_REACHED",
            reason="intraday_loss_limit_reached",
            details={
                "intraday_loss_pct": 12.0,
                "threshold_pct": 10.0,
                "daily_reference_capital": 1000.0,
            },
        ),
    )
    order_manager = SimpleNamespace(execute=AsyncMock(return_value=None))

    monitor = _build_monitor(repo, client, signal_engine, risk_manager, order_manager)
    await monitor._tick()

    kwargs = repo.update_signal_execution_outcome.call_args.kwargs
    assert kwargs["execution_status"] == "REJECTED_RISK_INTRADAY_LOSS_LIMIT"
    assert kwargs["execution_reason"] == "intraday_loss_limit_reached"


@pytest.mark.asyncio
async def test_tick_registra_desfecho_trade_opened() -> None:
    repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
        get_intraday_realized_pnl_usdt=AsyncMock(return_value=0.0),
        save_signal=AsyncMock(return_value="681cc200e8f9ff89bff8e463"),
        audit=AsyncMock(return_value=None),
        save_trade=AsyncMock(return_value="trade-123"),
        update_signal_execution_outcome=AsyncMock(return_value=True),
    )
    client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=pd.DataFrame({"close": [100.0, 101.0], "open": [99.0, 100.0]})
        ),
        fetch_usdt_balance=AsyncMock(return_value=100.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    signal_result = _build_signal_result()
    signal_engine = SimpleNamespace(evaluate=AsyncMock(return_value=signal_result))
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=SimpleNamespace(quantity=1.0)),
        consume_last_rejection=lambda: None,
    )
    trade = SimpleNamespace(
        status=TradeStatus.OPEN,
        symbol="BTCUSDT",
        direction=Direction.LONG,
        quantity=1.0,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        risk_amount=1.0,
        opened_at=datetime.now(UTC),
        to_dict=lambda: {"symbol": "BTCUSDT", "status": "OPEN"},
    )
    order_manager = SimpleNamespace(execute=AsyncMock(return_value=trade))

    monitor = _build_monitor(repo, client, signal_engine, risk_manager, order_manager)
    await monitor._tick()

    calls = repo.update_signal_execution_outcome.await_args_list
    assert len(calls) == 1
    kwargs = calls[0].kwargs
    assert kwargs["execution_status"] == "TRADE_OPENED"
    assert kwargs["trade_id"] == "trade-123"


@pytest.mark.asyncio
async def test_tick_persiste_diagnostico_de_avaliacao_sem_sinal() -> None:
    repo = SimpleNamespace(
        count_open_trades=AsyncMock(return_value=0),
        get_open_trades_for_symbol=AsyncMock(return_value=[]),
        get_intraday_realized_pnl_usdt=AsyncMock(return_value=0.0),
        save_signal=AsyncMock(return_value="unused"),
        audit=AsyncMock(return_value=None),
        update_signal_execution_outcome=AsyncMock(return_value=True),
    )
    client = SimpleNamespace(
        fetch_ohlcv_with_retry=AsyncMock(
            return_value=pd.DataFrame({"close": [100.0, 101.0], "open": [99.0, 100.0]})
        ),
        fetch_usdt_balance=AsyncMock(return_value=100.0),
        get_quantity_precision=MagicMock(return_value=3),
    )
    evaluation = SimpleNamespace(
        to_dict=lambda: {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "decision": "NO_SIGNAL",
            "signal_generated": False,
            "reason": "long_missing:close_above_fractal;short_missing:ao_negative",
        }
    )
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=NullSignalResult(reason="conditions_not_met")),
        consume_last_evaluation=MagicMock(return_value=evaluation),
    )
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=None),
        consume_last_rejection=lambda: None,
    )
    order_manager = SimpleNamespace(execute=AsyncMock(return_value=None))

    monitor = _build_monitor(repo, client, signal_engine, risk_manager, order_manager)
    await monitor._tick()

    repo.audit.assert_awaited_once_with("signal_evaluated", evaluation.to_dict())
    repo.save_signal.assert_not_awaited()
