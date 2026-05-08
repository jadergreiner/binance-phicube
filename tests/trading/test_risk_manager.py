from __future__ import annotations

from src.strategy.signal_engine import Direction, Signal
from src.trading.risk_manager import PositionSize, RiskManager


def _signal(
    *,
    entry: float = 100.0,
    stop: float = 95.0,
    take_profit: float = 110.0,
    direction: Direction = Direction.LONG,
) -> Signal:
    return Signal(
        symbol="BTCUSDT",
        timeframe="4h",
        direction=direction,
        entry_price=entry,
        stop_loss=stop,
        take_profit=take_profit,
        fractal_ref=96.0,
    )


class TestRiskManager:
    def test_calculate_success_without_scaling(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=10,
            max_capital_allocation_pct=50.0,
            min_notional=5.0,
        )
        signal = _signal(entry=100.0, stop=95.0)

        pos = manager.calculate(signal, available_balance=1000.0, quantity_precision=3)

        assert isinstance(pos, PositionSize)
        assert pos is not None
        assert pos.symbol == "BTCUSDT"
        assert pos.direction == Direction.LONG
        assert pos.quantity == 2.0
        assert pos.notional == 200.0
        assert pos.margin_required == 20.0
        assert pos.risk_amount == 10.0

    def test_calculate_scales_down_by_max_allocation(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=2,
            max_capital_allocation_pct=10.0,
            min_notional=5.0,
        )
        signal = _signal(entry=100.0, stop=99.0, take_profit=102.0)

        pos = manager.calculate(signal, available_balance=1000.0, quantity_precision=3)

        assert pos is None

    def test_returns_none_for_zero_stop_distance(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=5,
            max_capital_allocation_pct=30.0,
        )
        signal = _signal(entry=100.0, stop=100.0)

        assert manager.calculate(signal, available_balance=1000.0) is None
        rejection = manager.consume_last_rejection()
        assert rejection is not None
        assert rejection.code == "ZERO_STOP_DISTANCE"
        assert rejection.reason == "stop_distance_zero"

    def test_returns_none_when_rounding_turns_qty_zero(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=0.001,
            leverage=20,
            max_capital_allocation_pct=100.0,
            min_notional=0.0,
        )
        signal = _signal(entry=100.0, stop=50.0)

        # raw qty is tiny and rounds to 0 with precision=3
        assert manager.calculate(signal, available_balance=100.0, quantity_precision=3) is None
        rejection = manager.consume_last_rejection()
        assert rejection is not None
        assert rejection.code == "QTY_ZERO_AFTER_ROUNDING"

    def test_returns_none_when_below_min_notional(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=0.1,
            leverage=20,
            max_capital_allocation_pct=100.0,
            min_notional=50.0,
        )
        signal = _signal(entry=100.0, stop=90.0)

        # qty should be 0.01, notional=1.0 < min_notional
        assert manager.calculate(signal, available_balance=100.0, quantity_precision=3) is None
        rejection = manager.consume_last_rejection()
        assert rejection is not None
        assert rejection.code == "MIN_NOTIONAL_NOT_MET"

    def test_loga_warning_quando_excede_max_capital_allocation(self, capsys) -> None:
        manager = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=2,
            max_capital_allocation_pct=10.0,
            min_notional=5.0,
        )
        signal = _signal(entry=100.0, stop=99.0, take_profit=102.0)

        pos = manager.calculate(signal, available_balance=1000.0, quantity_precision=3)
        captured = capsys.readouterr()

        assert pos is None
        assert "position_rejected" in captured.out
        assert "max_capital_allocation_exceeded" in captured.out
        rejection = manager.consume_last_rejection()
        assert rejection is not None
        assert rejection.code == "MAX_CAPITAL_ALLOCATION_EXCEEDED"

    def test_position_to_dict(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=10,
            max_capital_allocation_pct=50.0,
        )
        signal = _signal(entry=100.0, stop=95.0)

        pos = manager.calculate(signal, available_balance=1000.0, quantity_precision=3)
        assert pos is not None

        payload = pos.to_dict()
        assert payload["symbol"] == "BTCUSDT"
        assert payload["direction"] == "LONG"
        assert payload["quantity"] == 2.0
        assert payload["risk_amount"] == 10.0
        assert manager.last_rejection is None
