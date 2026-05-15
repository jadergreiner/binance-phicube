from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Metrics:
    total_trades: int
    win_rate_pct: float
    total_pnl_usdt: float
    avg_rrr: float
    max_drawdown_usdt: float
    profit_factor: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "total_trades": self.total_trades,
            "win_rate_pct": self.win_rate_pct,
            "total_pnl_usdt": self.total_pnl_usdt,
            "avg_rrr": self.avg_rrr,
            "max_drawdown_usdt": self.max_drawdown_usdt,
            "profit_factor": self.profit_factor,
        }


def compute_metrics(
    pnls: Sequence[float],
    rrrs: Sequence[float] | None = None,
) -> Metrics:
    """Calcula métricas de performance a partir de PnLs e RRRs normalizados.

    Contratos semânticos:
    - `profit_factor` é normalizado para `0.0` quando `gross_loss == 0`.
    - `max_drawdown_usdt` é sempre não-positivo (`<= 0.0`).
    """
    if not pnls:
        return Metrics(
            total_trades=0,
            win_rate_pct=0.0,
            total_pnl_usdt=0.0,
            avg_rrr=0.0,
            max_drawdown_usdt=0.0,
            profit_factor=0.0,
        )

    total = len(pnls)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    total_pnl = sum(pnls)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    win_rate = len(wins) / total * 100.0
    avg_rrr = (sum(rrrs) / len(rrrs)) if rrrs else 0.0

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for pnl in pnls:
        equity += pnl
        if equity > peak:
            peak = equity
        drawdown = equity - peak
        if drawdown < max_drawdown:
            max_drawdown = drawdown

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    return Metrics(
        total_trades=total,
        win_rate_pct=round(win_rate, 2),
        total_pnl_usdt=round(total_pnl, 4),
        avg_rrr=round(avg_rrr, 4),
        max_drawdown_usdt=round(max_drawdown, 4),
        profit_factor=round(profit_factor, 4),
    )
