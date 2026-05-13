from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from src.strategy.signal_engine import SignalResult
from src.trading.middlewares import (
    CalculateRiskMiddleware,
    EvaluateSignalMiddleware,
    ExecuteTradeMiddleware,
    FetchCandlesMiddleware,
    NotifyMiddleware,
    ValidateLimitsMiddleware,
)
from src.trading.order_manager import TradeStatus
from src.trading.tick_pipeline import TickContext, TickPipeline


class TestTickPipelineIntegration:
    async def test_pipeline_full_success(self):
        # Setup mocks
        client = MagicMock()
        df = MagicMock()
        df.iloc = MagicMock(return_value=df)
        df.reset_index = MagicMock(return_value=df)
        client.fetch_ohlcv_with_retry = AsyncMock(return_value=df)
        client.fetch_usdt_balance = AsyncMock(return_value=1000.0)
        client.get_quantity_precision = MagicMock(return_value=3)

        repo = MagicMock()
        repo.count_open_trades = AsyncMock(return_value=0)
        repo.get_open_trades_for_symbol = AsyncMock(return_value=[])
        repo.get_intraday_realized_pnl_usdt = AsyncMock(return_value=0.0)
        repo.save_trade = AsyncMock(return_value="trade_123")
        repo.audit = AsyncMock()

        signal_engine = MagicMock()
        signal_result = SignalResult(
            direction="LONG",
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
        )
        signal_engine.evaluate = AsyncMock(return_value=signal_result)
        signal_engine.consume_last_evaluation = MagicMock(return_value=None)

        risk_manager = MagicMock()
        position = MagicMock()
        position.symbol = "BTCUSDT"
        position.quantity = 0.1
        risk_manager.calculate = MagicMock(return_value=position)
        risk_manager.consume_last_rejection = MagicMock(return_value=None)

        order_manager = MagicMock()
        trade = MagicMock()
        trade.symbol = "BTCUSDT"
        trade.status = TradeStatus.OPEN
        trade.to_dict = MagicMock(return_value={"symbol": "BTCUSDT"})
        order_manager.execute = AsyncMock(return_value=trade)

        notifier = MagicMock()
        notifier.send = AsyncMock()

        # Build pipeline
        pipeline = (
            TickPipeline()
            .use(FetchCandlesMiddleware(client, warmup_candles=200))
            .use(ValidateLimitsMiddleware(repo, max_open_positions=3))
            .use(EvaluateSignalMiddleware(signal_engine))
            .use(CalculateRiskMiddleware(client, risk_manager, repo))
            .use(ExecuteTradeMiddleware(order_manager, repo))
            .use(NotifyMiddleware(notifier))
        )

        context = TickContext(symbol="BTCUSDT", timeframe="15m")
        result = await pipeline.execute(context)

        assert not result.aborted
        assert result.trade is not None
        assert result.metrics["trade_id"] == "trade_123"
        assert "middlewares" in result.metrics
        assert len(result.metrics["middlewares"]) == 6

    async def test_pipeline_aborted_early(self):
        # Setup mocks - max positions reached
        client = MagicMock()
        df = MagicMock()
        df.iloc = MagicMock(return_value=df)
        df.reset_index = MagicMock(return_value=df)
        client.fetch_ohlcv_with_retry = AsyncMock(return_value=df)

        repo = MagicMock()
        repo.count_open_trades = AsyncMock(return_value=3)
        repo.get_open_trades_for_symbol = AsyncMock(return_value=[])

        signal_engine = MagicMock()
        risk_manager = MagicMock()
        order_manager = MagicMock()
        notifier = MagicMock()

        pipeline = (
            TickPipeline()
            .use(FetchCandlesMiddleware(client, warmup_candles=200))
            .use(ValidateLimitsMiddleware(repo, max_open_positions=3))
            .use(EvaluateSignalMiddleware(signal_engine))
            .use(CalculateRiskMiddleware(client, risk_manager, repo))
            .use(ExecuteTradeMiddleware(order_manager, repo))
            .use(NotifyMiddleware(notifier))
        )

        context = TickContext(symbol="BTCUSDT", timeframe="15m")
        result = await pipeline.execute(context)

        assert result.aborted
        assert result.abort_reason is not None
        assert "max_positions_reached" in result.abort_reason
        # Only first 2 middlewares should have metrics (fetch + validate)
        assert len(result.metrics.get("middlewares", {})) == 2

    async def test_pipeline_metrics_collection(self):
        client = MagicMock()
        df = MagicMock()
        df.iloc = MagicMock(return_value=df)
        df.reset_index = MagicMock(return_value=df)
        client.fetch_ohlcv_with_retry = AsyncMock(return_value=df)
        client.fetch_usdt_balance = AsyncMock(return_value=1000.0)
        client.get_quantity_precision = MagicMock(return_value=3)

        repo = MagicMock()
        repo.count_open_trades = AsyncMock(return_value=0)
        repo.get_open_trades_for_symbol = AsyncMock(return_value=[])
        repo.get_intraday_realized_pnl_usdt = AsyncMock(return_value=0.0)
        repo.save_trade = AsyncMock(return_value="trade_123")
        repo.audit = AsyncMock()

        signal_engine = MagicMock()
        signal_result = SignalResult(
            direction="LONG",
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
        )
        signal_engine.evaluate = AsyncMock(return_value=signal_result)
        signal_engine.consume_last_evaluation = MagicMock(return_value=None)

        risk_manager = MagicMock()
        position = MagicMock()
        position.symbol = "BTCUSDT"
        risk_manager.calculate = MagicMock(return_value=position)
        risk_manager.consume_last_rejection = MagicMock(return_value=None)

        order_manager = MagicMock()
        trade = MagicMock()
        trade.symbol = "BTCUSDT"
        trade.status = TradeStatus.OPEN
        trade.to_dict = MagicMock(return_value={"symbol": "BTCUSDT"})
        order_manager.execute = AsyncMock(return_value=trade)

        notifier = MagicMock()
        notifier.send = AsyncMock()

        pipeline = (
            TickPipeline()
            .use(FetchCandlesMiddleware(client, warmup_candles=200))
            .use(ValidateLimitsMiddleware(repo, max_open_positions=3))
            .use(EvaluateSignalMiddleware(signal_engine))
            .use(CalculateRiskMiddleware(client, risk_manager, repo))
            .use(ExecuteTradeMiddleware(order_manager, repo))
            .use(NotifyMiddleware(notifier))
        )

        context = TickContext(symbol="BTCUSDT", timeframe="15m")
        result = await pipeline.execute(context)

        middlewares_metrics = result.metrics.get("middlewares", {})
        for name, metrics in middlewares_metrics.items():
            assert "duration" in metrics
            assert "success" in metrics
            assert metrics["success"] is True
            assert metrics["aborted"] is False
