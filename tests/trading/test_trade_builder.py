"""
Testes para TradeBuilder — Builder Pattern.

Cobertura: casos feliz, validação incremental, build_failed.
"""

from __future__ import annotations

import pytest

from src.config.settings import ExitStrategy
from src.strategy.signal_engine import Direction, Signal
from src.trading.order_manager import TradeStatus
from src.trading.risk_manager import PositionSize
from src.trading.trade_builder import TradeBuilder, TradeBuilderError


@pytest.fixture
def sample_signal() -> Signal:
    return Signal(
        symbol="BTCUSDT",
        timeframe="15m",
        direction=Direction.LONG,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        fractal_ref=49500.0,
    )


@pytest.fixture
def sample_position() -> PositionSize:
    return PositionSize(
        symbol="BTCUSDT",
        direction=Direction.LONG,
        quantity=0.1,
        notional=5000.0,
        margin_required=1000.0,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        risk_amount=100.0,
    )


class TestTradeBuilderHappyPath:
    def test_build_trade_with_all_fields(self, sample_signal, sample_position):
        builder = TradeBuilder()
        trade = (
            builder.with_entry(sample_signal, sample_position)
            .with_orders("entry-123", "sl-456", ["tp-789"])
            .with_exit_strategy(ExitStrategy.FIXED, [{"qty_pct": 50.0, "price_distance_pct": 2.0}])
            .build()
        )

        assert trade.symbol == "BTCUSDT"
        assert trade.timeframe == "15m"
        assert trade.direction == Direction.LONG
        assert trade.entry_price == 50000.0
        assert trade.stop_loss == 49000.0
        assert trade.take_profit == 52000.0
        assert trade.quantity == 0.1
        assert trade.risk_amount == 100.0
        assert trade.margin_used == 1000.0
        assert trade.entry_order_id == "entry-123"
        assert trade.sl_order_id == "sl-456"
        assert trade.tp_order_id == "tp-789"
        assert trade.status == TradeStatus.OPEN
        assert trade.exit_strategy == ExitStrategy.FIXED
        assert trade.tp_levels is not None

    def test_build_trade_minimal(self, sample_signal, sample_position):
        trade = (
            TradeBuilder()
            .with_entry(sample_signal, sample_position)
            .with_orders("entry-123", None, None)
            .build()
        )

        assert trade.symbol == "BTCUSDT"
        assert trade.entry_order_id == "entry-123"
        assert trade.sl_order_id is None
        assert trade.tp_order_id is None


class TestTradeBuilderValidation:
    def test_missing_symbol(self, sample_signal, sample_position):
        builder = TradeBuilder()
        builder.with_entry(sample_signal, sample_position)
        builder._symbol = None  # forçar invalidação
        with pytest.raises(TradeBuilderError, match="symbol is required"):
            builder.build()

    def test_missing_timeframe(self, sample_signal, sample_position):
        builder = TradeBuilder()
        builder.with_entry(sample_signal, sample_position)
        builder._timeframe = None
        with pytest.raises(TradeBuilderError, match="timeframe is required"):
            builder.build()

    def test_zero_entry_price(self, sample_signal, sample_position):
        builder = TradeBuilder()
        builder.with_entry(sample_signal, sample_position)
        builder._entry_price = 0.0
        with pytest.raises(TradeBuilderError, match="entry_price must be > 0"):
            builder.build()

    def test_zero_quantity(self, sample_signal, sample_position):
        builder = TradeBuilder()
        builder.with_entry(sample_signal, sample_position)
        builder._quantity = 0.0
        with pytest.raises(TradeBuilderError, match="quantity must be > 0"):
            builder.build()

    def test_equal_stop_and_take_profit(self, sample_signal, sample_position):
        builder = TradeBuilder()
        builder.with_entry(sample_signal, sample_position)
        builder._stop_loss = 50000.0
        builder._take_profit = 50000.0
        with pytest.raises(TradeBuilderError, match="stop_loss and take_profit must differ"):
            builder.build()

    def test_missing_entry_order_id(self, sample_signal, sample_position):
        builder = TradeBuilder()
        builder.with_entry(sample_signal, sample_position)
        builder._entry_order_id = None
        with pytest.raises(TradeBuilderError, match="entry_order_id is required"):
            builder.build()


class TestTradeBuilderFailed:
    def test_build_failed_trade(self, sample_signal, sample_position):
        trade = TradeBuilder().build_failed(sample_signal, sample_position, "entry-123")

        assert trade.symbol == "BTCUSDT"
        assert trade.status == TradeStatus.FAILED
        assert trade.entry_order_id == "entry-123"
        assert trade.entry_price == 50000.0
