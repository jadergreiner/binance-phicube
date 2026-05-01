"""
Entry point — Binance Phicube Auto Trade System.

Loop principal:
    Para cada (símbolo, timeframe) configurado, executa um monitor independente
    que acorda a cada candle fechada, avalia sinais e abre operações quando válido.

Controles de segurança:
    - Não abre nova posição se já existe uma aberta no mesmo símbolo
    - Respeita o limite global de posições abertas (max_open_positions)
    - Ignora a última candle (possivelmente incompleta) na avaliação de sinais
"""
from __future__ import annotations

import asyncio
import signal
import sys

from src.config.settings import get_settings
from src.exchange.binance_client import BinanceClient
from src.monitoring.logger import configure_logging, get_logger
from src.storage.repository import MongoRepository
from src.strategy.signal_engine import SignalEngine
from src.trading.order_manager import OrderManager, TradeStatus
from src.trading.risk_manager import RiskManager

logger = get_logger(__name__)

# Seconds to wait between each candle-close poll per (symbol, timeframe)
_TIMEFRAME_SECONDS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
}


class TradingMonitor:
    """Monitors one (symbol, timeframe) pair and acts on closed candles."""

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        client: BinanceClient,
        repo: MongoRepository,
        signal_engine: SignalEngine,
        risk_manager: RiskManager,
        order_manager: OrderManager,
        max_open_positions: int,
        warmup_candles: int,
    ) -> None:
        self._symbol = symbol
        self._timeframe = timeframe
        self._client = client
        self._repo = repo
        self._signal_engine = signal_engine
        self._risk_manager = risk_manager
        self._order_manager = order_manager
        self._max_positions = max_open_positions
        self._warmup_candles = warmup_candles
        self._interval = _TIMEFRAME_SECONDS.get(timeframe, 900)

    async def run(self) -> None:
        logger.info("monitor_started", symbol=self._symbol, timeframe=self._timeframe)

        while True:
            try:
                await self._tick()
            except asyncio.CancelledError:
                logger.info("monitor_stopped", symbol=self._symbol, timeframe=self._timeframe)
                return
            except Exception as exc:
                logger.error(
                    "monitor_tick_error",
                    symbol=self._symbol,
                    timeframe=self._timeframe,
                    error=str(exc),
                    exc_info=True,
                )

            await asyncio.sleep(self._interval)

    async def _tick(self) -> None:
        # Fetch closed candles — request one extra and drop the last (open) candle
        df = await self._client.fetch_ohlcv_with_retry(
            symbol=self._symbol,
            timeframe=self._timeframe,
            limit=self._warmup_candles + 1,
        )
        # Discard the last (potentially incomplete) candle
        df = df.iloc[:-1].reset_index(drop=True)

        # Check if we can open new positions
        total_open = await self._repo.count_open_trades()
        if total_open >= self._max_positions:
            logger.debug(
                "max_positions_reached",
                open=total_open,
                max=self._max_positions,
            )
            return

        # Check if this symbol already has an open position
        symbol_trades = await self._repo.get_open_trades_for_symbol(self._symbol)
        if symbol_trades:
            logger.debug("symbol_already_in_trade", symbol=self._symbol)
            return

        # Evaluate signal
        signal = self._signal_engine.evaluate(self._symbol, self._timeframe, df)
        if signal is None:
            return

        # Persist signal regardless of execution
        await self._repo.save_signal(signal.to_dict())
        await self._repo.audit("signal_detected", signal.to_dict())

        # Calculate position size
        balance = await self._client.fetch_usdt_balance()
        if balance <= 0:
            logger.warning("zero_balance", symbol=self._symbol)
            return

        qty_precision = self._client.get_quantity_precision(self._symbol)
        position = self._risk_manager.calculate(signal, balance, qty_precision)
        if position is None:
            logger.warning("position_size_rejected", symbol=self._symbol)
            return

        # Execute trade
        trade = await self._order_manager.execute(signal, position)
        if trade is None:
            logger.error("trade_execution_failed", symbol=self._symbol)
            return

        trade_id = await self._repo.save_trade(trade)
        await self._repo.audit(
            "trade_opened",
            {"trade_id": trade_id, **trade.to_dict()},
        )

        if trade.status == TradeStatus.FAILED:
            logger.error("trade_saved_as_failed", symbol=self._symbol, trade_id=trade_id)


async def _main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    logger.info(
        "phicube_starting",
        symbols=settings.symbols,
        timeframes=settings.timeframes,
        testnet=settings.binance_testnet,
        leverage=settings.leverage,
        risk_pct=settings.risk_per_trade_pct,
    )

    client = BinanceClient(settings)
    await client.connect()

    repo = MongoRepository(settings.mongodb_uri, settings.mongodb_database)
    await repo.setup_indexes()

    signal_engine = SignalEngine(risk_reward_ratio=settings.risk_reward_ratio)
    risk_manager = RiskManager(
        risk_per_trade_pct=settings.risk_per_trade_pct,
        leverage=settings.leverage,
        max_capital_allocation_pct=settings.max_capital_allocation_pct,
    )
    order_manager = OrderManager(client, leverage=settings.leverage)

    monitors = [
        TradingMonitor(
            symbol=symbol,
            timeframe=timeframe,
            client=client,
            repo=repo,
            signal_engine=signal_engine,
            risk_manager=risk_manager,
            order_manager=order_manager,
            max_open_positions=settings.max_open_positions,
            warmup_candles=settings.warmup_candles,
        )
        for symbol in settings.symbols
        for timeframe in settings.timeframes
    ]

    tasks = [asyncio.create_task(m.run()) for m in monitors]

    # Graceful shutdown on SIGINT / SIGTERM
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: _shutdown(tasks, client, repo))

    logger.info("phicube_running", monitor_count=len(tasks))

    try:
        await asyncio.gather(*tasks)
    finally:
        await client.close()
        await repo.close()
        logger.info("phicube_stopped")


def _shutdown(
    tasks: list[asyncio.Task],
    client: BinanceClient,
    repo: MongoRepository,
) -> None:
    logger.info("shutdown_signal_received")
    for task in tasks:
        task.cancel()


def entrypoint() -> None:
    """CLI entry point registered in pyproject.toml."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(_main())


if __name__ == "__main__":
    entrypoint()
