from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.common.serialization import auto_dict


@auto_dict
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
    # --- SPEC_028: custos realistas ---
    entry_fee: float = 0.0
    exit_fee: float = 0.0
    slippage_entry_pct: float = 0.0
    slippage_exit_pct: float = 0.0
    slippage_entry_usdt: float = 0.0
    slippage_exit_usdt: float = 0.0
    pnl_gross_usdt: float = 0.0
    pnl_net_usdt: float = 0.0


@auto_dict
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
    # --- SPEC_028: resultado realista ---
    gross: BacktestResult | None = None
    net: BacktestResult | None = None
    total_fees_usdt: float = 0.0
    total_slippage_usdt: float = 0.0
    warnings: list[str] = field(default_factory=list)
