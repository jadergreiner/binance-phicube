from __future__ import annotations

import math
from datetime import UTC, datetime

import pandas as pd

# Duração de cada timeframe em milissegundos — usado para paginação por since
_TF_MS: dict[str, int] = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "6h": 21_600_000,
    "8h": 28_800_000,
    "12h": 43_200_000,
    "1d": 86_400_000,
}

from src.backtest.models import BacktestResult, BacktestTrade
from src.config.settings import Settings
from src.exchange.binance_client import BinanceClient
from src.strategy.signal_engine import SignalEngine


class BacktestEngine:
    def __init__(self, settings: Settings, client: BinanceClient) -> None:
        self._settings = settings
        self._client = client
        self._signal_engine = SignalEngine(risk_reward_ratio=settings.risk_reward_ratio)

    async def _fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        candle_ms = _TF_MS.get(timeframe, 60_000)
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        since = now_ms - limit * candle_ms

        frames: list[pd.DataFrame] = []
        while True:
            fetched = sum(len(f) for f in frames)
            remaining = limit - fetched
            if remaining <= 0:
                break
            batch = min(1000, remaining)
            df = await self._client.fetch_ohlcv(symbol, timeframe, limit=batch, since=since)
            if df.empty:
                break
            frames.append(df)
            # Avança since para depois da última vela recebida — evita re-buscar as mesmas velas
            last_ts_ms = pd.Timestamp(df["open_time"].iloc[-1]).value // 1_000_000
            since = last_ts_ms + candle_ms
            if len(df) < batch:
                break

        if not frames:
            return pd.DataFrame()
        result = pd.concat(frames, ignore_index=True)
        result = result.drop_duplicates(subset=["open_time"]).reset_index(drop=True)
        return result

    def _calc_metrics(self, trades: list[BacktestTrade]) -> dict[str, float]:
        if not trades:
            return {
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "total_pnl_usdt": 0.0,
                "avg_rrr": 0.0,
                "max_drawdown_usdt": 0.0,
                "profit_factor": 0.0,
            }

        wins = [t for t in trades if t.pnl_usdt > 0]
        losses = [t for t in trades if t.pnl_usdt <= 0]
        win_rate = len(wins) / len(trades) * 100.0
        total_pnl = sum(t.pnl_usdt for t in trades)
        avg_rrr = sum(t.rrr_realizado for t in trades) / len(trades)

        gross_profit = sum(t.pnl_usdt for t in wins)
        gross_loss = abs(sum(t.pnl_usdt for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else math.inf

        # pico→vale sobre equity acumulada
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for t in trades:
            equity += t.pnl_usdt
            if equity > peak:
                peak = equity
            drawdown = equity - peak
            if drawdown < max_drawdown:
                max_drawdown = drawdown

        return {
            "total_trades": len(trades),
            "win_rate_pct": round(win_rate, 2),
            "total_pnl_usdt": round(total_pnl, 4),
            "avg_rrr": round(avg_rrr, 4),
            "max_drawdown_usdt": round(max_drawdown, 4),
            "profit_factor": round(profit_factor, 4) if not math.isinf(profit_factor) else 0.0,
        }

    async def run(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 1000,
        initial_balance: float = 1000.0,
    ) -> BacktestResult:
        df = await self._fetch_ohlcv(symbol, timeframe, limit)
        warmup = self._settings.warmup_candles

        if df.empty or len(df) <= warmup:
            return BacktestResult(
                symbol=symbol,
                timeframe=timeframe,
                candles_used=0,
                generated_at=datetime.utcnow(),
            )

        trades: list[BacktestTrade] = []
        open_trade: dict | None = None

        for i in range(warmup, len(df)):
            row = df.iloc[i]
            high = float(row["high"])
            low = float(row["low"])

            if open_trade is not None:
                direction = open_trade["direction"]
                tp = open_trade["tp"]
                sl = open_trade["sl"]
                entry = open_trade["entry"]
                close_reason: str | None = None
                exit_price: float | None = None

                if direction == "LONG":
                    if high >= tp:
                        close_reason = "TP"
                        exit_price = tp
                    elif low <= sl:
                        close_reason = "SL"
                        exit_price = sl
                else:
                    if low <= tp:
                        close_reason = "TP"
                        exit_price = tp
                    elif high >= sl:
                        close_reason = "SL"
                        exit_price = sl

                if close_reason is not None and exit_price is not None:
                    if direction == "LONG":
                        pnl = (exit_price - entry) * initial_balance / entry
                    else:
                        pnl = (entry - exit_price) * initial_balance / entry

                    risk_dist = abs(entry - sl)
                    reward_dist = abs(exit_price - entry)
                    rrr = reward_dist / risk_dist if risk_dist > 0 else 0.0

                    trades.append(
                        BacktestTrade(
                            symbol=symbol,
                            timeframe=timeframe,
                            direction=direction,
                            entry_price=entry,
                            sl_price=sl,
                            tp_price=tp,
                            entry_candle_idx=open_trade["entry_idx"],
                            exit_candle_idx=i,
                            exit_price=exit_price,
                            close_reason=close_reason,
                            pnl_usdt=round(pnl, 4),
                            rrr_realizado=round(rrr, 4),
                        )
                    )
                    open_trade = None

            if open_trade is None:
                window = df.iloc[: i + 1]
                signal = self._signal_engine.evaluate(symbol, timeframe, window)
                if signal is not None:
                    open_trade = {
                        "direction": signal.direction.value,
                        "entry": signal.entry_price,
                        "sl": signal.stop_loss,
                        "tp": signal.take_profit,
                        "entry_idx": i,
                    }

        metrics = self._calc_metrics(trades)
        return BacktestResult(
            symbol=symbol,
            timeframe=timeframe,
            candles_used=len(df) - warmup,
            trades=trades,
            total_trades=metrics["total_trades"],
            win_rate_pct=metrics["win_rate_pct"],
            total_pnl_usdt=metrics["total_pnl_usdt"],
            avg_rrr=metrics["avg_rrr"],
            max_drawdown_usdt=metrics["max_drawdown_usdt"],
            profit_factor=metrics["profit_factor"],
            generated_at=datetime.utcnow(),
        )
