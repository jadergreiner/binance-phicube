from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from src.exchange.base_client import TradingClient
from src.strategy.signal_engine import Direction, Signal
from src.trading.order_manager import OrderManager
from src.trading.risk_manager import PositionSize


def _sample_signal() -> Signal:
    return Signal(
        symbol="BTCUSDT",
        timeframe="4h",
        direction=Direction.LONG,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        fractal_ref=48500.0,
        detected_at=datetime.now(UTC),
    )


def _sample_position() -> PositionSize:
    return PositionSize(
        symbol="BTCUSDT",
        direction=Direction.LONG,
        quantity=0.001,
        notional=50.0,
        margin_required=25.0,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        risk_amount=10.0,
    )


def _mock_client() -> AsyncMock:
    client = AsyncMock()
    client.set_leverage = AsyncMock()
    client.set_margin_mode = AsyncMock()
    client.create_market_order = AsyncMock(return_value={"id": "entry-1", "average": "50000.0"})
    client.round_price = AsyncMock(side_effect=[49000.0, 52000.0])
    client.create_stop_loss_order = AsyncMock(return_value={"id": "sl-1"})
    client.create_take_profit_order = AsyncMock(return_value={"id": "tp-1"})
    client.cancel_all_orders = AsyncMock()
    return client


class StubTradingClient(TradingClient):
    def __init__(self) -> None:
        self.cancel_all_orders_calls = 0

    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    async def fetch_ohlcv(
        self, symbol: str, timeframe: str, limit: int = 200, since: int | None = None
    ) -> pd.DataFrame:
        return pd.DataFrame()

    async def fetch_ohlcv_with_retry(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        retries: int | None = None,
        base_delay: float | None = None,
    ) -> pd.DataFrame:
        return pd.DataFrame()

    async def fetch_ticker(self, symbol: str) -> dict[str, object]:
        return {}

    async def fetch_usdt_balance(self) -> float:
        return 0.0

    async def fetch_balance(self) -> dict[str, object]:
        return {}

    async def set_leverage(self, symbol: str, leverage: int) -> None: ...

    async def set_margin_mode(self, symbol: str, mode: str = "isolated") -> None: ...

    async def create_market_order(
        self, symbol: str, side: str, quantity: float, params: dict[str, object] | None = None
    ) -> dict[str, object]:
        return {"id": "entry-1", "average": "50000.0"}

    async def create_stop_loss_order(
        self, symbol: str, side: str, quantity: float, stop_price: float
    ) -> dict[str, object]:
        return {"id": "sl-1"}

    async def create_take_profit_order(
        self, symbol: str, side: str, quantity: float, take_profit_price: float
    ) -> dict[str, object]:
        return {"id": "tp-1"}

    async def create_trailing_stop_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        activation_price: float,
        callback_rate: float,
    ) -> dict[str, object]:
        return {"id": "ts-1"}

    async def cancel_all_orders(self, symbol: str) -> None:
        self.cancel_all_orders_calls += 1

    async def fetch_open_orders(self, symbol: str) -> list[dict[str, object]]:
        return []

    async def fetch_order(self, order_id: str, symbol: str) -> dict[str, object]:
        return {}

    async def fetch_open_positions(self) -> list[dict[str, object]]:
        return []

    async def fetch_position_risk(self, *, symbol: str | None = None) -> list[dict[str, object]]:
        return []

    def get_quantity_precision(self, symbol: str) -> int:
        return 3

    def round_quantity(self, symbol: str, qty: float) -> float:
        return qty

    def round_price(self, symbol: str, price: float) -> float:
        return price


@pytest.mark.asyncio
async def test_execute_rolls_back_when_stop_loss_creation_fails() -> None:
    client = _mock_client()
    client.create_stop_loss_order.side_effect = Exception("SL failed")
    notifier = AsyncMock()
    manager = OrderManager(client=client, leverage=5, notifier=notifier)

    result = await manager.execute(_sample_signal(), _sample_position())

    assert result.is_err()
    error = result.unwrap_err()
    assert error.code == "SL_TP_ORDER_FAILED"
    # Command Pattern: pipeline rollback chama cancel_all_orders para cada comando executado
    # (MarketOrder = 1 chamada)
    assert client.cancel_all_orders.call_count == 1
    assert client.cancel_all_orders.call_args_list[-1] == (("BTCUSDT",),)


@pytest.mark.asyncio
async def test_execute_rolls_back_when_take_profit_creation_fails() -> None:
    client = _mock_client()
    client.create_take_profit_order.side_effect = Exception("TP failed")
    manager = OrderManager(client=client, leverage=5, notifier=None)

    result = await manager.execute(_sample_signal(), _sample_position())

    assert result.is_err()
    error = result.unwrap_err()
    assert error.code == "SL_TP_ORDER_FAILED"
    # Command Pattern: pipeline rollback chama cancel_all_orders para cada comando executado
    # (StopLoss + MarketOrder = 2 chamadas)
    assert client.cancel_all_orders.call_count == 2
    assert client.cancel_all_orders.call_args_list[-1] == (("BTCUSDT",),)


@pytest.mark.asyncio
async def test_execute_accepts_generic_trading_client_stub() -> None:
    client = StubTradingClient()
    manager = OrderManager(client=client, leverage=5, notifier=None)

    result = await manager.execute(_sample_signal(), _sample_position())

    assert result.is_ok()
    trade = result.unwrap()
    assert trade.entry_order_id == "entry-1"
    assert trade.sl_order_id == "sl-1"
    assert trade.tp_order_ids == ["tp-1"]
