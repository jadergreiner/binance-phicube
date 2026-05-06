from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BacktestTrade:
    symbol: str
    timeframe: str
    direction: str
    entry_price: float
    sl_price: float
    tp_price: float
    entry_candle_idx: int
    exit_candle_idx: int
    exit_price: float
    close_reason: str
    pnl_usdt: float
    rrr_realizado: float


@dataclass
class BacktestResult:
    symbol: str
    timeframe: str
    candles_used: int
    trades: list[BacktestTrade] = field(default_factory=list)
    total_trades: int = 0
    win_rate_pct: float = 0.0
    total_pnl_usdt: float = 0.0
    avg_rrr: float = 0.0
    max_drawdown_usdt: float = 0.0
    profit_factor: float = 0.0
    generated_at: datetime = field(default_factory=datetime.utcnow)
