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

Se margin_required > max_capital_allocation, a operação é bloqueada.

SPEC_029 — Position Sizing por ATR:
    Adiciona modo "atr" que calcula position size usando ATR (Average True Range)
    com guarda de segurança: effective_stop = max(fractal_sl_distance, atr * multiplier).
    Risco fixo em USDT independente do par.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from src.config.settings import SizingMode
from src.monitoring.logger import get_logger
from src.strategy.indicators import atr as atr_func
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


@dataclass(frozen=True)
class RiskRejection:
    code: str
    reason: str
    details: dict[str, Any]


class RiskManager:
    """Calcula o tamanho de posição respeitando todos os limites de risco."""

    def __init__(
        self,
        risk_per_trade_pct: float,
        leverage: int,
        max_capital_allocation_pct: float,
        min_notional: float = 5.0,  # mínimo nocional aceito pela Binance Futures
        intraday_loss_limit_pct: float = 10.0,
        # SPEC_029 — Position Sizing por ATR
        sizing_mode: SizingMode = SizingMode.FIXED,
        risk_per_trade_usdt: float = 5.0,
        atr_period: int = 14,
        atr_multiplier: float = 1.5,
        min_position_usdt: float = 10.0,
        max_position_usdt: float = 500.0,
        get_atr_multiplier_override: Callable[[str], float | None] | None = None,
    ) -> None:
        self._risk_pct = risk_per_trade_pct
        self._leverage = leverage
        self._max_alloc_pct = max_capital_allocation_pct
        self._min_notional = min_notional
        self._intraday_loss_limit_pct = intraday_loss_limit_pct
        self._last_rejection: RiskRejection | None = None
        self._daily_reference_capital: float | None = None
        self._daily_reference_day: datetime.date | None = None
        # SPEC_029
        self._sizing_mode = sizing_mode
        self._risk_per_trade_usdt = risk_per_trade_usdt
        self._atr_period = atr_period
        self._atr_multiplier = atr_multiplier
        self._min_position_usdt = min_position_usdt
        self._max_position_usdt = max_position_usdt
        self._get_atr_multiplier_override = get_atr_multiplier_override

    @property
    def last_rejection(self) -> RiskRejection | None:
        return self._last_rejection

    def consume_last_rejection(self) -> RiskRejection | None:
        rejection = self._last_rejection
        self._last_rejection = None
        return rejection

    def _set_rejection(self, *, code: str, reason: str, details: dict[str, Any]) -> None:
        self._last_rejection = RiskRejection(code=code, reason=reason, details=details)

    def calculate(
        self,
        signal: Signal,
        available_balance: float,
        quantity_precision: int = 3,
        intraday_realized_pnl_usdt: float = 0.0,
        now_utc: datetime | None = None,
        df: pd.DataFrame | None = None,
    ) -> PositionSize | None:
        """Calculate position size for a given signal and available balance.

        Args:
            signal: Sinal de trading com entry/stop/take_profit.
            available_balance: Saldo disponível em USDT.
            quantity_precision: Precisão de quantidade da exchange.
            intraday_realized_pnl_usdt: PnL realizado intraday.
            now_utc: Timestamp UTC atual.
            df: OHLCV DataFrame (obrigatório para SIZING_MODE=atr).

        Returns:
            PositionSize ou None se violar constraints de risco.

        Modo ATR (SPEC_029):
            Se SIZING_MODE=atr e df for fornecido, calcula position size
            com effective_stop = max(fractal_sl_distance, atr * atr_multiplier).
            Se ATR indisponível, faz fallback silencioso para fixed.
        """
        self._last_rejection = None
        now = now_utc.astimezone(UTC) if now_utc else datetime.now(UTC)
        self._refresh_intraday_reference(available_balance, now)
        if self._intraday_loss_limit_reached(intraday_realized_pnl_usdt):
            daily_reference_capital = self._daily_reference_capital or available_balance
            intraday_loss_pct = round(
                abs(intraday_realized_pnl_usdt) / daily_reference_capital * 100,
                4,
            )
            self._set_rejection(
                code="INTRADAY_LOSS_LIMIT_REACHED",
                reason="intraday_loss_limit_reached",
                details={
                    "intraday_loss_pct": intraday_loss_pct,
                    "threshold_pct": self._intraday_loss_limit_pct,
                    "daily_reference_capital": round(daily_reference_capital, 4),
                    "intraday_realized_pnl_usdt": round(intraday_realized_pnl_usdt, 4),
                },
            )
            logger.warning(
                "intraday_loss_limit_reached",
                symbol=signal.symbol,
                intraday_loss_pct=intraday_loss_pct,
                threshold_pct=self._intraday_loss_limit_pct,
                daily_reference_capital=round(daily_reference_capital, 4),
                intraday_realized_pnl_usdt=round(intraday_realized_pnl_usdt, 4),
            )
            return None

        stop_distance = abs(signal.entry_price - signal.stop_loss)
        if stop_distance == 0:
            self._set_rejection(
                code="ZERO_STOP_DISTANCE",
                reason="stop_distance_zero",
                details={},
            )
            logger.warning("zero_stop_distance", symbol=signal.symbol)
            return None

        # ── SPEC_029 — ATR mode ─────────────────────────────────────────────
        if self._sizing_mode == SizingMode.ATR and df is not None:
            result = self._calculate_atr(
                signal=signal,
                stop_distance=stop_distance,
                quantity_precision=quantity_precision,
                df=df,
            )
            if result is not None:
                return result
            # Fallback silencioso: se ATR falhou, tenta fixed
            logger.info(
                "atr_fallback_to_fixed",
                symbol=signal.symbol,
            )

        return self._calculate_fixed(
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=signal.entry_price,
            stop_price=signal.stop_loss,
            take_profit=signal.take_profit,
            available_balance=available_balance,
            quantity_precision=quantity_precision,
        )

    def _get_effective_multiplier(self, symbol: str) -> float:
        """Retorna atr_multiplier considerando override por par."""
        if self._get_atr_multiplier_override is not None:
            override = self._get_atr_multiplier_override(symbol)
            if override is not None:
                return override
        return self._atr_multiplier

    def _calculate_atr(
        self,
        signal: Signal,
        stop_distance: float,
        quantity_precision: int,
        df: pd.DataFrame,
    ) -> PositionSize | None:
        """Calculate position size using ATR mode (SPEC_029).

        effective_stop = max(fractal_sl_distance, atr_value * atr_multiplier)
        position_usdt = risk_per_trade_usdt * entry_price / effective_stop
        """
        # Calculate ATR
        atr_series = atr_func(
            df["close"],
            df["high"],
            df["low"],
            self._atr_period,
        )
        atr_value = atr_series.iloc[-1]

        # Fallback se ATR inválido
        if pd.isna(atr_value) or atr_value <= 0:
            logger.warning(
                "atr_value_invalid_fallback_to_fixed",
                symbol=signal.symbol,
                atr_value=atr_value,
                atr_period=self._atr_period,
                df_len=len(df),
            )
            return None

        # Effective stop com guard
        multiplier = self._get_effective_multiplier(signal.symbol)
        fractal_sl_distance = stop_distance
        effective_stop = max(fractal_sl_distance, atr_value * multiplier)

        # Position size em USDT
        position_usdt = self._risk_per_trade_usdt * signal.entry_price / effective_stop
        position_usdt = max(
            self._min_position_usdt,
            min(position_usdt, self._max_position_usdt),
        )

        # Quantidade do ativo
        raw_qty = position_usdt / signal.entry_price
        qty = round(raw_qty, quantity_precision)

        if qty <= 0:
            self._set_rejection(
                code="QTY_ZERO_AFTER_ROUNDING",
                reason="quantity_zero_after_rounding",
                details={"quantity_precision": quantity_precision},
            )
            logger.warning(
                "position_size_zero_after_rounding_atr",
                symbol=signal.symbol,
                position_usdt=round(position_usdt, 2),
            )
            return None

        # INV-029-05: risco real não excede 1.05x configurado
        actual_risk_usdt = qty * effective_stop
        max_risk_usdt = self._risk_per_trade_usdt * 1.05
        if actual_risk_usdt > max_risk_usdt:
            self._set_rejection(
                code="INV_029_05_RISK_EXCEEDED",
                reason="actual_risk_exceeds_tolerance",
                details={
                    "actual_risk_usdt": round(actual_risk_usdt, 4),
                    "max_risk_usdt": round(max_risk_usdt, 4),
                    "effective_stop": round(effective_stop, 4),
                    "atr_value": round(atr_value, 4),
                    "multiplier": multiplier,
                },
            )
            logger.error(
                "atr_sizing_risk_violation",
                symbol=signal.symbol,
                actual_risk_usdt=round(actual_risk_usdt, 2),
                max_risk_usdt=round(max_risk_usdt, 2),
                effective_stop=round(effective_stop, 2),
                atr_value=round(atr_value, 4),
                multiplier=multiplier,
            )
            return None

        # Log estruturado para auditoria
        logger.info(
            "atr_sizing_calculated",
            symbol=signal.symbol,
            direction=signal.direction.value,
            atr_value=round(atr_value, 4),
            fractal_sl_distance=round(fractal_sl_distance, 2),
            effective_stop=round(effective_stop, 2),
            position_usdt=round(position_usdt, 2),
            quantity=qty,
            risk_per_trade_usdt=self._risk_per_trade_usdt,
            multiplier=multiplier,
            sizing_mode="atr",
        )

        return PositionSize(
            symbol=signal.symbol,
            direction=signal.direction,
            quantity=qty,
            notional=round(qty * signal.entry_price, 4),
            margin_required=round(qty * signal.entry_price / self._leverage, 4),
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            risk_amount=self._risk_per_trade_usdt,
        )

    def _calculate_fixed(
        self,
        symbol: str,
        direction: Direction,
        entry_price: float,
        stop_price: float,
        take_profit: float,
        available_balance: float,
        quantity_precision: int = 3,
    ) -> PositionSize | None:
        """Comportamento legado: position sizing por % do saldo (risk_per_trade_pct)."""
        stop_distance = abs(entry_price - stop_price)

        # Raw position size based on fixed-risk formula
        risk_amount = available_balance * (self._risk_pct / 100.0)
        raw_qty = risk_amount / stop_distance

        # Notional and margin check
        notional = raw_qty * entry_price
        margin_required = notional / self._leverage
        max_allowed_margin = available_balance * (self._max_alloc_pct / 100.0)

        if margin_required > max_allowed_margin:
            self._set_rejection(
                code="MAX_CAPITAL_ALLOCATION_EXCEEDED",
                reason="max_capital_allocation_exceeded",
                details={
                    "margin_required": round(margin_required, 4),
                    "max_allowed_margin": round(max_allowed_margin, 4),
                },
            )
            logger.warning(
                "position_rejected",
                symbol=symbol,
                reason="max_capital_allocation_exceeded",
                margin_required=round(margin_required, 4),
                max_allowed_margin=round(max_allowed_margin, 4),
            )
            return None

        # Round to exchange precision
        qty = round(raw_qty, quantity_precision)

        if qty <= 0:
            self._set_rejection(
                code="QTY_ZERO_AFTER_ROUNDING",
                reason="quantity_zero_after_rounding",
                details={"quantity_precision": quantity_precision},
            )
            logger.warning("position_size_zero_after_rounding", symbol=symbol)
            return None

        # Enforce minimum notional
        if qty * entry_price < self._min_notional:
            self._set_rejection(
                code="MIN_NOTIONAL_NOT_MET",
                reason="below_min_notional",
                details={
                    "notional": round(qty * entry_price, 2),
                    "min_notional": self._min_notional,
                },
            )
            logger.warning(
                "below_min_notional",
                symbol=symbol,
                notional=round(qty * entry_price, 2),
                min_notional=self._min_notional,
            )
            return None

        pos = PositionSize(
            symbol=symbol,
            direction=direction,
            quantity=qty,
            notional=round(qty * entry_price, 4),
            margin_required=round(margin_required, 4),
            entry_price=entry_price,
            stop_loss=stop_price,
            take_profit=take_profit,
            risk_amount=round(risk_amount, 4),
        )

        self._last_rejection = None
        logger.info("position_size_calculated", **pos.to_dict())
        return pos

    def _refresh_intraday_reference(self, available_balance: float, now_utc: datetime) -> None:
        day = now_utc.date()
        if self._daily_reference_day != day or self._daily_reference_capital is None:
            self._daily_reference_day = day
            self._daily_reference_capital = available_balance

    def _intraday_loss_limit_reached(self, intraday_realized_pnl_usdt: float) -> bool:
        if intraday_realized_pnl_usdt >= 0:
            return False
        if not self._daily_reference_capital or self._daily_reference_capital <= 0:
            return False
        loss_pct = abs(intraday_realized_pnl_usdt) / self._daily_reference_capital * 100
        return loss_pct >= self._intraday_loss_limit_pct
