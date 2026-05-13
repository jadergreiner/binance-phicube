from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from src.monitoring.logger import get_logger
from src.trading.tick_pipeline import TickContext

logger = get_logger(__name__)


class CalculateRiskMiddleware:
    """Middleware para calcular tamanho da posição."""

    def __init__(self, client: Any, risk_manager: Any, repo: Any) -> None:
        self._client = client
        self._risk_manager = risk_manager
        self._repo = repo

    async def process(
        self,
        context: TickContext,
        next: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        if context.signal is None:
            context.abort("calculate_risk_no_signal")
            return

        balance = await self._client.fetch_usdt_balance()
        if balance <= 0:
            context.abort(f"zero_or_negative_balance: {balance}")
            return

        qty_precision = self._client.get_quantity_precision(context.symbol)
        intraday_realized_pnl_usdt = await self._repo.get_intraday_realized_pnl_usdt()

        # Convert SignalResult to Signal if needed
        signal = context.signal
        if hasattr(signal, "direction") and not hasattr(signal, "entry_price"):
            # It's already a Signal-like object
            pass
        else:
            from src.strategy.signal_engine import Direction, Signal

            signal = Signal(
                symbol=context.symbol,
                timeframe=context.timeframe,
                direction=Direction(signal.direction),
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                fractal_ref=(signal.metadata or {}).get("fractal_ref", 0.0)
                if hasattr(signal, "metadata")
                else 0.0,
            )

        position = self._risk_manager.calculate(
            signal,
            balance,
            qty_precision,
            intraday_realized_pnl_usdt=intraday_realized_pnl_usdt,
            df=context.df,
        )

        if position is None:
            rejection = self._risk_manager.consume_last_rejection()
            reason = rejection.reason if rejection else "unknown"
            context.abort(f"position_size_rejected: {reason}")
            return

        context.position = position
        await next()
