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


def _build_signal_result(plugin_name: str | None = None) -> SignalResult:
    metadata = {"fractal_ref": 99.0}
    if plugin_name:
        metadata["plugin"] = plugin_name
    return SignalResult(
        direction="LONG",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        metadata=metadata,
    )


def _build_monitor(
    repo,
    client,
    signal_engine,
    risk_manager,
    order_manager,
    *,
    ml_support_service=None,
    phicube_mode: str = "shadow",
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
        phicube_mode=phicube_mode,
        ml_support_service=ml_support_service,
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
    from src.common.result import err

    rejection = RiskRejection(
        code="MAX_CAPITAL_ALLOCATION_EXCEEDED",
        reason="max_capital_allocation_exceeded",
        details={"margin_required": 10.0, "max_allowed_margin": 5.0},
    )
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=err(rejection)),
        consume_last_rejection=lambda: rejection,
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
    from src.common.result import err

    rejection = RiskRejection(
        code="INTRADAY_LOSS_LIMIT_REACHED",
        reason="intraday_loss_limit_reached",
        details={
            "intraday_loss_pct": 12.0,
            "threshold_pct": 10.0,
            "daily_reference_capital": 1000.0,
        },
    )
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=err(rejection)),
        consume_last_rejection=lambda: rejection,
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
    from src.common.result import ok

    position = SimpleNamespace(quantity=1.0)
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=ok(position)),
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
    order_manager = SimpleNamespace(execute=AsyncMock(return_value=ok(trade)))

    monitor = _build_monitor(repo, client, signal_engine, risk_manager, order_manager)
    await monitor._tick()

    calls = repo.update_signal_execution_outcome.await_args_list
    assert len(calls) == 1
    kwargs = calls[0].kwargs
    assert kwargs["execution_status"] == "TRADE_OPENED"
    assert kwargs["trade_id"] == "trade-123"


@pytest.mark.asyncio
async def test_tick_registra_desfecho_entry_open_no_protection() -> None:
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
    from src.common.result import OrderError, err, ok

    position = SimpleNamespace(quantity=1.0)
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=ok(position)),
        consume_last_rejection=lambda: None,
    )
    order_error = OrderError(
        code="SL_TP_ORDER_FAILED",
        message="sl/tp failed after entry",
        details={
            "execution_status": "ENTRY_OPEN_NO_PROTECTION",
            "entry_executed": True,
            "entry_order_id": "entry-123",
            "entry_price": 100.0,
            "quantity": 1.0,
        },
    )
    order_manager = SimpleNamespace(execute=AsyncMock(return_value=err(order_error)))

    monitor = _build_monitor(repo, client, signal_engine, risk_manager, order_manager)
    await monitor._tick()

    kwargs = repo.update_signal_execution_outcome.call_args.kwargs
    assert kwargs["execution_status"] == "ENTRY_OPEN_NO_PROTECTION"
    assert kwargs["execution_reason"] == "entry_opened_but_sl_tp_failed"


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
        evaluate=AsyncMock(
            return_value=NullSignalResult(
                reason="conditions_not_met",
                metadata={
                    "reason": "conditions_not_met",
                    "rule_hits": ["RN-PHI-005:consolidation", "RN-PHI-024:chart_confirmed"],
                    "market_state": "consolidation",
                },
            )
        ),
        consume_last_evaluation=MagicMock(return_value=evaluation),
    )
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=None),
        consume_last_rejection=lambda: None,
    )
    order_manager = SimpleNamespace(execute=AsyncMock(return_value=None))

    monitor = _build_monitor(repo, client, signal_engine, risk_manager, order_manager)
    await monitor._tick()

    events = [call.args[0] for call in repo.audit.await_args_list]
    assert "signal_evaluated" in events
    assert "signal_cycle_diagnostic" in events
    cycle_events = [c for c in repo.audit.await_args_list if c.args[0] == "signal_cycle_diagnostic"]
    payload = cycle_events[-1].args[1]
    assert payload["phicube_mode"] == "shadow"
    assert payload["reason"] == "conditions_not_met"
    assert payload["market_state"] == "consolidation"
    assert payload["rule_hits"] == ["RN-PHI-005:consolidation", "RN-PHI-024:chart_confirmed"]
    assert isinstance(payload["explicacao_humana"], str)
    repo.save_signal.assert_not_awaited()


@pytest.mark.asyncio
async def test_tick_rejeicao_risco_registra_signal_cycle_diagnostic() -> None:
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
    from src.common.result import err

    rejection = RiskRejection(
        code="QTY_ZERO_AFTER_ROUNDING",
        reason="quantity_zero_after_rounding",
        details={"qty_raw": 0.00049, "qty_rounded": 0.0, "quantity_precision": 3},
    )
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=err(rejection)),
        consume_last_rejection=lambda: rejection,
    )
    order_manager = SimpleNamespace(execute=AsyncMock(return_value=None))

    monitor = _build_monitor(repo, client, signal_engine, risk_manager, order_manager)
    await monitor._tick()

    cycle_events = [
        call for call in repo.audit.await_args_list if call.args[0] == "signal_cycle_diagnostic"
    ]
    assert cycle_events
    payload = cycle_events[-1].args[1]
    assert payload["final_status"] == "REJECTED_BY_RISK"
    assert payload["risk_reason"] == "quantity_zero_after_rounding"


@pytest.mark.asyncio
async def test_tick_ml_shadow_mode_registra_campos_no_diagnostico() -> None:
    from src.strategy.ml_support import MlOperationalSupportService

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
    evaluation = SimpleNamespace(to_dict=lambda: {"decision": "NO_SIGNAL"})
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=NullSignalResult(reason="regime_lateral_blocked")),
        consume_last_evaluation=MagicMock(return_value=evaluation),
    )
    risk_manager = SimpleNamespace(calculate=MagicMock(return_value=None))
    order_manager = SimpleNamespace(execute=AsyncMock(return_value=None))
    ml_support = MlOperationalSupportService(enabled=True, shadow_mode=True)

    monitor = _build_monitor(
        repo,
        client,
        signal_engine,
        risk_manager,
        order_manager,
        ml_support_service=ml_support,
    )
    await monitor._tick()

    cycle_events = [c for c in repo.audit.await_args_list if c.args[0] == "signal_cycle_diagnostic"]
    payload = cycle_events[-1].args[1]
    assert payload["ml_enabled"] is True
    assert payload["ml_shadow_mode"] is True
    assert payload["phicube_mode"] == "shadow"
    assert payload["ml_score"] is not None
    assert payload["ml_reason"] == "regime_lateral_blocked"


@pytest.mark.asyncio
async def test_tick_registra_phicube_mode_advisory_no_diagnostico() -> None:
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
    evaluation = SimpleNamespace(to_dict=lambda: {"decision": "NO_SIGNAL"})
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=NullSignalResult(reason="conditions_not_met")),
        consume_last_evaluation=MagicMock(return_value=evaluation),
    )
    risk_manager = SimpleNamespace(calculate=MagicMock(return_value=None))
    order_manager = SimpleNamespace(execute=AsyncMock(return_value=None))

    monitor = _build_monitor(
        repo,
        client,
        signal_engine,
        risk_manager,
        order_manager,
        phicube_mode="advisory",
    )
    await monitor._tick()

    cycle_events = [c for c in repo.audit.await_args_list if c.args[0] == "signal_cycle_diagnostic"]
    payload = cycle_events[-1].args[1]
    assert payload["phicube_mode"] == "advisory"


@pytest.mark.asyncio
async def test_tick_shadow_mode_blocks_phicube_order_execution() -> None:
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
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=_build_signal_result(plugin_name="phicube")),
    )
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=None),
        consume_last_rejection=lambda: None,
    )
    order_manager = SimpleNamespace(execute=AsyncMock(return_value=None))

    monitor = _build_monitor(
        repo,
        client,
        signal_engine,
        risk_manager,
        order_manager,
        phicube_mode="shadow",
    )
    await monitor._tick()

    kwargs = repo.update_signal_execution_outcome.call_args.kwargs
    assert kwargs["execution_status"] == "REJECTED_MODE_GATED"
    assert kwargs["execution_reason"] == "phicube_mode_shadow_blocked_execution"
    order_manager.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_tick_advisory_mode_blocks_phicube_order_execution() -> None:
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
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=_build_signal_result(plugin_name="phicube")),
    )
    risk_manager = SimpleNamespace(
        calculate=MagicMock(return_value=None),
        consume_last_rejection=lambda: None,
    )
    order_manager = SimpleNamespace(execute=AsyncMock(return_value=None))

    monitor = _build_monitor(
        repo,
        client,
        signal_engine,
        risk_manager,
        order_manager,
        phicube_mode="advisory",
    )
    await monitor._tick()

    kwargs = repo.update_signal_execution_outcome.call_args.kwargs
    assert kwargs["execution_status"] == "REJECTED_MODE_GATED"
    assert kwargs["execution_reason"] == "phicube_mode_advisory_blocked_execution"
    order_manager.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_tick_ml_falha_nao_interrompe_ciclo_e_faz_fallback_bo_puro() -> None:
    class _BrokenMlSupport:
        def evaluate(self, **_kwargs):
            raise RuntimeError("ml down")

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
    evaluation = SimpleNamespace(to_dict=lambda: {"decision": "NO_SIGNAL"})
    signal_engine = SimpleNamespace(
        evaluate=AsyncMock(return_value=NullSignalResult(reason="conditions_not_met")),
        consume_last_evaluation=MagicMock(return_value=evaluation),
    )
    risk_manager = SimpleNamespace(calculate=MagicMock(return_value=None))
    order_manager = SimpleNamespace(execute=AsyncMock(return_value=None))

    monitor = _build_monitor(
        repo,
        client,
        signal_engine,
        risk_manager,
        order_manager,
        ml_support_service=_BrokenMlSupport(),
    )
    await monitor._tick()

    cycle_events = [c for c in repo.audit.await_args_list if c.args[0] == "signal_cycle_diagnostic"]
    payload = cycle_events[-1].args[1]
    assert payload["final_status"] == "NO_SETUP_DETECTED"
    assert str(payload["ml_reason"]).startswith("ml_support_error:")
