"""Serviço de assertividade por símbolo/período para dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from src.common.metrics import compute_metrics


class PeriodStrategy(Protocol):
    def resolve(
        self, *, now: datetime, start: datetime | None, end: datetime | None
    ) -> tuple[datetime, datetime]:
        """Resolve janela temporal UTC para a consulta."""


class LastDaysPeriodStrategy:
    def __init__(self, days: int) -> None:
        self._days = days

    def resolve(
        self, *, now: datetime, start: datetime | None, end: datetime | None
    ) -> tuple[datetime, datetime]:
        end_utc = (end or now).astimezone(UTC)
        return end_utc - timedelta(days=self._days), end_utc


class CustomPeriodStrategy:
    def resolve(
        self, *, now: datetime, start: datetime | None, end: datetime | None
    ) -> tuple[datetime, datetime]:
        if start is None or end is None:
            raise ValueError("custom_period_requires_start_and_end")
        return start.astimezone(UTC), end.astimezone(UTC)


def resolve_period_strategy(period: str) -> PeriodStrategy:
    normalized = (period or "30d").lower()
    if normalized == "7d":
        return LastDaysPeriodStrategy(days=7)
    if normalized == "30d":
        return LastDaysPeriodStrategy(days=30)
    if normalized == "90d":
        return LastDaysPeriodStrategy(days=90)
    if normalized == "custom":
        return CustomPeriodStrategy()
    raise ValueError("invalid_period")


def parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


@dataclass
class AssertivenessQuery:
    symbol: str | None
    timeframe: str | None
    period: str
    start: datetime | None
    end: datetime | None
    order_by: str
    order_dir: str


class AssertivenessFacade:
    """Facade para orquestrar coleta e agregação da assertividade."""

    def __init__(self, repository: Any) -> None:
        self._repo = repository

    @staticmethod
    def _is_trade_opened_status(status: str | None) -> bool:
        normalized = str(status or "").upper()
        return normalized in {"TRADE_OPENED", "ENTRY_OPEN_NO_PROTECTION"}

    async def build(self, query: AssertivenessQuery) -> dict[str, Any]:
        now = datetime.now(UTC)
        strategy = resolve_period_strategy(query.period)
        start, end = strategy.resolve(now=now, start=query.start, end=query.end)
        if start > end:
            raise ValueError("invalid_period_range")

        signals = await self._repo.get_signals_in_period(
            start=start, end=end, symbol=query.symbol, timeframe=query.timeframe
        )
        trades = await self._repo.get_closed_trades_in_period(
            start=start, end=end, symbol=query.symbol, timeframe=query.timeframe
        )

        by_symbol: dict[str, dict[str, Any]] = {}
        for signal in signals:
            symbol = str(signal.get("symbol") or "unknown")
            row = by_symbol.setdefault(
                symbol, {"signals": 0, "opened_from_signals": 0, "trades": []}
            )
            row["signals"] += 1
            if self._is_trade_opened_status(signal.get("execution_status")):
                row["opened_from_signals"] += 1
        for trade in trades:
            symbol = str(trade.get("symbol") or "unknown")
            row = by_symbol.setdefault(
                symbol, {"signals": 0, "opened_from_signals": 0, "trades": []}
            )
            row["trades"].append(trade)

        ranking = []
        for symbol, group in by_symbol.items():
            group_trades = group["trades"]
            pnls = [float(t.get("pnl_usdt") or 0.0) for t in group_trades]
            rrrs = [
                float(t.get("pnl_usdt") or 0.0) / float(t.get("risk_amount"))
                for t in group_trades
                if float(t.get("risk_amount") or 0.0) > 0
            ]
            metrics = compute_metrics(pnls, rrrs).to_dict()
            total_signals = int(group["signals"])
            total_trades = int(metrics["total_trades"])
            opened_from_signals = int(group.get("opened_from_signals") or 0)
            conversion = (
                round((opened_from_signals / total_signals) * 100, 2) if total_signals > 0 else 0.0
            )
            ranking.append(
                {
                    "symbol": symbol,
                    "assertiveness_pct": float(metrics["win_rate_pct"]),
                    "total_signals": total_signals,
                    "total_trades": total_trades,
                    "signal_to_trade_conversion_pct": conversion,
                    "pnl_usdt": float(metrics["total_pnl_usdt"]),
                    "profit_factor": float(metrics["profit_factor"]),
                    "max_drawdown_usdt": float(metrics["max_drawdown_usdt"]),
                }
            )

        reverse = query.order_dir.lower() == "desc"
        if query.order_by in {"assertiveness_pct", "pnl_usdt"}:
            ranking.sort(key=lambda row: float(row.get(query.order_by) or 0.0), reverse=reverse)

        period_days = max(1, int((end - start).total_seconds() // 86400))
        bucket_mode = "daily" if period_days <= 30 else "weekly"
        timeline = self._build_timeline(trades, bucket_mode)

        total_signals = len(signals)
        opened_from_signals = sum(
            1
            for signal in signals
            if self._is_trade_opened_status(signal.get("execution_status"))
        )
        overall_pnls = [float(t.get("pnl_usdt") or 0.0) for t in trades]
        overall_rrrs = [
            float(t.get("pnl_usdt") or 0.0) / float(t.get("risk_amount"))
            for t in trades
            if float(t.get("risk_amount") or 0.0) > 0
        ]
        overall = compute_metrics(overall_pnls, overall_rrrs).to_dict()
        total_trades = int(overall["total_trades"])
        overall_conversion = (
            round((opened_from_signals / total_signals) * 100, 2) if total_signals > 0 else 0.0
        )
        summary = {
            "assertiveness_pct": float(overall["win_rate_pct"]),
            "total_signals": total_signals,
            "total_trades": total_trades,
            "signal_to_trade_conversion_pct": overall_conversion,
            "pnl_usdt": float(overall["total_pnl_usdt"]),
            "profit_factor": float(overall["profit_factor"]),
            "max_drawdown_usdt": float(overall["max_drawdown_usdt"]),
        }
        return {
            "period": query.period,
            "start": start,
            "end": end,
            "bucket_mode": bucket_mode,
            "summary": summary,
            "ranking": ranking,
            "timeline": timeline,
        }

    def _build_timeline(
        self, trades: list[dict[str, Any]], bucket_mode: str
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for trade in trades:
            closed_at = trade.get("closed_at")
            if not isinstance(closed_at, datetime):
                continue
            dt = closed_at.astimezone(UTC)
            if bucket_mode == "weekly":
                year, week, _ = dt.isocalendar()
                key = f"{year}-W{week:02d}"
            else:
                key = dt.strftime("%Y-%m-%d")
            grouped.setdefault(key, []).append(trade)

        rows: list[dict[str, Any]] = []
        for bucket, bucket_trades in grouped.items():
            pnls = [float(t.get("pnl_usdt") or 0.0) for t in bucket_trades]
            rrrs = [
                float(t.get("pnl_usdt") or 0.0) / float(t.get("risk_amount"))
                for t in bucket_trades
                if float(t.get("risk_amount") or 0.0) > 0
            ]
            metrics = compute_metrics(pnls, rrrs).to_dict()
            rows.append(
                {
                    "bucket": bucket,
                    "assertiveness_pct": float(metrics["win_rate_pct"]),
                    "total_trades": int(metrics["total_trades"]),
                    "pnl_usdt": float(metrics["total_pnl_usdt"]),
                }
            )
        rows.sort(key=lambda row: row["bucket"])
        return rows
