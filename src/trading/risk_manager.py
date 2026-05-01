"""
Gestão de risco e position sizing.

Cálculo baseado em risco fixo por operação (% do capital disponível),
respeitando os limites de alavancagem e capital máximo alocado.

Fórmula do position size:
    risk_amount = balance * (risk_pct / 100)
    stop_distance = |entry_price - stop_loss|
    position_size = risk_amount / stop_distance   (em contratos/moeda)
    notional = position_size * entry_price
    margin_required = notional / leverage

Se margin_required > max_capital_allocation, reduz position_size proporcionalmente.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.monitoring.logger import get_logger
from src.strategy.signal_engine import Direction, Signal

logger = get_logger(__name__)


@dataclass(frozen=True)
class PositionSize:
    symbol: str
    direction: Direction
    quantity: float  # contratos (unidades do ativo base)
    notional: float  # valor nocional em USDT
    margin_required: float  # margem necessária em USDT
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_amount: float  # USDT arriscados nesta operação

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction.value,
            "quantity": self.quantity,
            "notional": self.notional,
            "margin_required": self.margin_required,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_amount": self.risk_amount,
        }


class RiskManager:
    """Calcula o tamanho de posição respeitando todos os limites de risco."""

    def __init__(
        self,
        risk_per_trade_pct: float,
        leverage: int,
        max_capital_allocation_pct: float,
        min_notional: float = 5.0,  # mínimo nocional aceito pela Binance Futures
    ) -> None:
        self._risk_pct = risk_per_trade_pct
        self._leverage = leverage
        self._max_alloc_pct = max_capital_allocation_pct
        self._min_notional = min_notional

    def calculate(
        self,
        signal: Signal,
        available_balance: float,
        quantity_precision: int = 3,
    ) -> PositionSize | None:
        """Calculate position size for a given signal and available balance.

        Returns None if the trade would violate any risk constraint.
        """
        stop_distance = abs(signal.entry_price - signal.stop_loss)
        if stop_distance == 0:
            logger.warning("zero_stop_distance", symbol=signal.symbol)
            return None

        # Raw position size based on fixed-risk formula
        risk_amount = available_balance * (self._risk_pct / 100.0)
        raw_qty = risk_amount / stop_distance

        # Notional and margin check
        notional = raw_qty * signal.entry_price
        margin_required = notional / self._leverage
        max_allowed_margin = available_balance * (self._max_alloc_pct / 100.0)

        if margin_required > max_allowed_margin:
            # Scale down to fit within max allocation
            scale = max_allowed_margin / margin_required
            raw_qty *= scale
            notional *= scale
            margin_required = max_allowed_margin
            risk_amount *= scale
            logger.info(
                "position_scaled_down",
                symbol=signal.symbol,
                reason="max_capital_allocation",
                scale=round(scale, 4),
            )

        # Round to exchange precision
        qty = round(raw_qty, quantity_precision)

        if qty <= 0:
            logger.warning("position_size_zero_after_rounding", symbol=signal.symbol)
            return None

        # Enforce minimum notional
        if qty * signal.entry_price < self._min_notional:
            logger.warning(
                "below_min_notional",
                symbol=signal.symbol,
                notional=round(qty * signal.entry_price, 2),
                min_notional=self._min_notional,
            )
            return None

        pos = PositionSize(
            symbol=signal.symbol,
            direction=signal.direction,
            quantity=qty,
            notional=round(qty * signal.entry_price, 4),
            margin_required=round(margin_required, 4),
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            risk_amount=round(risk_amount, 4),
        )

        logger.info("position_size_calculated", **pos.to_dict())
        return pos
