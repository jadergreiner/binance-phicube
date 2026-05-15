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

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from src.common.result import Result, RiskRejection, err, ok
from src.common.serialization import auto_dict
from src.config.settings import SizingMode
from src.monitoring.logger import get_logger
from src.strategy.indicators import atr as atr_func
from src.strategy.signal_engine import Direction, Signal

logger = get_logger(__name__)

DEAD_ZONE: float = 0.001  # D10: PnL abaixo deste valor não altera contadores CB


class _PredictiveBreakerStrategy:
    """Strategy para decidir skip preditivo baseado em ATR ratio histórico."""

    def should_skip(
        self,
        *,
        current_ratio: float,
        ratio_history: pd.Series,
        percentile: float,
    ) -> tuple[bool, float]:
        threshold = float(ratio_history.quantile(percentile))
        return current_ratio > threshold, threshold


@auto_dict
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


class RiskManager:
    """Calcula o tamanho de posição respeitando todos os limites de risco."""

    _predictive_skips_total: int = 0

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
        # SPEC_043 — Slippage Protection e Circuit Breaker
        get_portfolio_reduction: Callable[[], float] | None = None,
        max_position_pct: float = 0.0,
        consecutive_loss_threshold: int = 3,
        cb_risk_reduction_factor: float = 0.5,
        recovery_wins_needed: int = 1,
        circuit_breaker_enabled: bool = False,
        # SPEC_043 — Slippage parameters (refactored from getattr injection)
        slippage_validation_enabled: bool = False,
        slippage_tolerance_multiplier: float = 1.10,
        slippage_tolerance_reduced: float = 1.05,
        liq_map: dict[str, str] | None = None,
        slippage_map: dict[str, float] | None = None,
        predictive_breaker_enabled: bool = False,
        predictive_breaker_percentile: float = 0.85,
        predictive_breaker_window: int = 100,
        predictive_breaker_tiers: list[str] | None = None,
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
        # SPEC_043 — Slippage
        self._max_position_pct = max_position_pct
        # SPEC_043 — Circuit Breaker (State Pattern)
        self._consecutive_losses: int = 0
        self._circuit_breaker_active: bool = False
        self._recovery_wins_count: int = 0
        self._original_risk_per_trade_usdt: float = risk_per_trade_usdt
        self._consecutive_loss_threshold = consecutive_loss_threshold
        self._cb_risk_reduction_factor = cb_risk_reduction_factor
        self._recovery_wins_needed = recovery_wins_needed
        self._circuit_breaker_enabled = circuit_breaker_enabled
        self._cb_lock: asyncio.Lock = asyncio.Lock()
        self._slippage_validation_enabled = slippage_validation_enabled
        self._slippage_tolerance_multiplier = slippage_tolerance_multiplier
        self._slippage_tolerance_reduced = slippage_tolerance_reduced
        self._liq_map = liq_map or {}
        self._slippage_map = slippage_map or {}
        self._predictive_breaker_enabled = predictive_breaker_enabled
        self._predictive_breaker_percentile = predictive_breaker_percentile
        self._predictive_breaker_window = predictive_breaker_window
        self._predictive_breaker_tiers = set(predictive_breaker_tiers or ["low"])
        self._predictive_breaker_strategy = _PredictiveBreakerStrategy()
        # SPEC_043 — Portfolio CB Observer
        self._get_portfolio_reduction = get_portfolio_reduction

    @classmethod
    def get_predictive_skips_total(cls) -> int:
        return cls._predictive_skips_total

    @property
    def last_rejection(self) -> RiskRejection | None:
        return self._last_rejection

    def consume_last_rejection(self) -> RiskRejection | None:
        rejection = self._last_rejection
        self._last_rejection = None
        return rejection

    def _set_rejection(self, *, code: str, reason: str, details: dict[str, Any]) -> None:
        self._last_rejection = RiskRejection(code, reason, details)

    def calculate(
        self,
        signal: Signal,
        available_balance: float,
        quantity_precision: int = 3,
        intraday_realized_pnl_usdt: float = 0.0,
        now_utc: datetime | None = None,
        df: pd.DataFrame | None = None,
    ) -> Result[PositionSize, RiskRejection]:
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
            rejection = RiskRejection(
                code="INTRADAY_LOSS_LIMIT_REACHED",
                reason="intraday_loss_limit_reached",
                details={
                    "intraday_loss_pct": intraday_loss_pct,
                    "threshold_pct": self._intraday_loss_limit_pct,
                    "daily_reference_capital": round(daily_reference_capital, 4),
                    "intraday_realized_pnl_usdt": round(intraday_realized_pnl_usdt, 4),
                },
            )
            self._last_rejection = rejection
            logger.warning(
                "intraday_loss_limit_reached",
                symbol=signal.symbol,
                intraday_loss_pct=intraday_loss_pct,
                threshold_pct=self._intraday_loss_limit_pct,
                daily_reference_capital=round(daily_reference_capital, 4),
                intraday_realized_pnl_usdt=round(intraday_realized_pnl_usdt, 4),
            )
            return err(rejection)

        stop_distance = abs(signal.entry_price - signal.stop_loss)
        if stop_distance == 0:
            rejection = RiskRejection(
                code="ZERO_STOP_DISTANCE",
                reason="stop_distance_zero",
                details={},
            )
            self._last_rejection = rejection
            logger.warning("zero_stop_distance", symbol=signal.symbol)
            return err(rejection)

        gate_result = self._run_pre_trade_gates(
            signal=signal,
            available_balance=available_balance,
            stop_distance=stop_distance,
            quantity_precision=quantity_precision,
            df=df,
        )
        if gate_result is not None:
            return gate_result

        # ── SPEC_029 — ATR mode ─────────────────────────────────────────────
        if self._sizing_mode == SizingMode.ATR and df is not None:
            result = self._calculate_atr(
                signal=signal,
                stop_distance=stop_distance,
                quantity_precision=quantity_precision,
                df=df,
                available_balance=available_balance,
            )
            # Se ATR retornou Ok, retorna direto
            if result.is_ok():
                return result
            # Se ATR retornou Err, verifica se é fallback ou erro real
            if result.is_err():
                rejection = result.error  # type: ignore
                # Se é fallback (code="ATR_FALLBACK"), tenta fixed
                if rejection.code == "ATR_FALLBACK":
                    logger.info(
                        "atr_fallback_to_fixed",
                        symbol=signal.symbol,
                    )
                else:
                    # Erro real, não fallback
                    return result

        return self._calculate_fixed(
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=signal.entry_price,
            stop_price=signal.stop_loss,
            take_profit=signal.take_profit,
            available_balance=available_balance,
            quantity_precision=quantity_precision,
        )

    def _compute_atr_value(self, df: pd.DataFrame) -> float:
        """Calcula o valor do ATR para o DataFrame fornecido (SPEC_043 Facade).

        Retorna 0.0 se df for None, vazio ou não tiver candles suficientes.
        """
        if df is None or df.empty or len(df) < self._atr_period + 1:
            return 0.0
        atr_series = atr_func(
            df["close"],
            df["high"],
            df["low"],
            self._atr_period,
        )
        atr_value = atr_series.iloc[-1]
        if pd.isna(atr_value) or atr_value <= 0:
            return 0.0
        return float(atr_value)

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
        available_balance: float = 0.0,
    ) -> Result[PositionSize, RiskRejection]:
        """Calculate position size using ATR mode (SPEC_029).

        effective_stop = max(fractal_sl_distance, atr_value * atr_multiplier)
        position_usdt = risk_per_trade_usdt * entry_price / effective_stop
        """
        # Calculate ATR via Facade (SPEC_043)
        atr_value = self._compute_atr_value(df)

        # Fallback se ATR inválido
        if atr_value <= 0:
            logger.warning(
                "atr_value_invalid_fallback_to_fixed",
                symbol=signal.symbol,
                atr_value=atr_value,
                atr_period=self._atr_period,
                df_len=len(df),
            )
            # Retorna Err com code="ATR_FALLBACK" para sinalizar fallback ao fixed mode
            return err(
                RiskRejection(
                    code="ATR_FALLBACK",
                    reason="atr_value_invalid",
                    details={"atr_value": atr_value, "atr_period": self._atr_period},
                )
            )

        # Effective stop com guard
        multiplier = self._get_effective_multiplier(signal.symbol)
        fractal_sl_distance = stop_distance
        effective_stop = max(fractal_sl_distance, atr_value * multiplier)

        # Position size em USDT
        position_usdt = self.effective_risk_per_trade_usdt * signal.entry_price / effective_stop
        # SPEC_043 — max_position_pct: limite dinâmico como % do saldo
        effective_max_position = self._max_position_usdt
        if self._max_position_pct > 0 and available_balance > 0:
            max_by_pct = available_balance * self._max_position_pct / 100.0
            effective_max_position = min(self._max_position_usdt, max_by_pct)
        position_usdt = max(
            self._min_position_usdt,
            min(position_usdt, effective_max_position),
        )

        # Quantidade do ativo
        raw_qty = position_usdt / signal.entry_price
        qty = round(raw_qty, quantity_precision)

        if qty <= 0:
            rejection = RiskRejection(
                code="QTY_ZERO_AFTER_ROUNDING",
                reason="quantity_zero_after_rounding",
                details={"quantity_precision": quantity_precision},
            )
            self._last_rejection = rejection
            logger.warning(
                "position_size_zero_after_rounding_atr",
                symbol=signal.symbol,
                position_usdt=round(position_usdt, 2),
            )
            return err(rejection)

        # INV-029-05: risco real não excede 1.05x configurado
        actual_risk_usdt = qty * effective_stop
        max_risk_usdt = self.effective_risk_per_trade_usdt * 1.05
        if actual_risk_usdt > max_risk_usdt:
            rejection = RiskRejection(
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
            self._last_rejection = rejection
            logger.error(
                "atr_sizing_risk_violation",
                symbol=signal.symbol,
                actual_risk_usdt=round(actual_risk_usdt, 2),
                max_risk_usdt=round(max_risk_usdt, 2),
                effective_stop=round(effective_stop, 2),
                atr_value=round(atr_value, 4),
                multiplier=multiplier,
            )
            return err(rejection)

        # SPEC_043 — Slippage gate (Facade)
        if not self._check_slippage_gate(
            actual_risk_usdt=actual_risk_usdt,
            base_risk_usdt=self.effective_risk_per_trade_usdt,
            symbol=signal.symbol,
            quantity=qty,
            entry_price=signal.entry_price,
            atr_value=atr_value,
        ):
            # _check_slippage_gate já setou _last_rejection
            rejection = self._last_rejection
            if rejection is None:
                rejection = RiskRejection(
                    code="SLIPPAGE_EXCEEDS_TOLERANCE",
                    reason="slippage_check_failed",
                    details={},
                )
            return err(rejection)

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
            risk_per_trade_usdt=self.effective_risk_per_trade_usdt,
            multiplier=multiplier,
            sizing_mode="atr",
        )

        pos = PositionSize(
            symbol=signal.symbol,
            direction=signal.direction,
            quantity=qty,
            notional=round(qty * signal.entry_price, 4),
            margin_required=round(qty * signal.entry_price / self._leverage, 4),
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            risk_amount=self.effective_risk_per_trade_usdt,
        )
        return ok(pos)

    def _calculate_fixed(
        self,
        symbol: str,
        direction: Direction,
        entry_price: float,
        stop_price: float,
        take_profit: float,
        available_balance: float,
        quantity_precision: int = 3,
    ) -> Result[PositionSize, RiskRejection]:
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
            rejection = RiskRejection(
                code="MAX_CAPITAL_ALLOCATION_EXCEEDED",
                reason="max_capital_allocation_exceeded",
                details={
                    "margin_required": round(margin_required, 4),
                    "max_allowed_margin": round(max_allowed_margin, 4),
                },
            )
            self._last_rejection = rejection
            logger.warning(
                "position_rejected",
                symbol=symbol,
                reason="max_capital_allocation_exceeded",
                margin_required=round(margin_required, 4),
                max_allowed_margin=round(max_allowed_margin, 4),
            )
            return err(rejection)

        # Round to exchange precision
        qty = round(raw_qty, quantity_precision)

        if qty <= 0:
            rejection = RiskRejection(
                code="QTY_ZERO_AFTER_ROUNDING",
                reason="quantity_zero_after_rounding",
                details={"quantity_precision": quantity_precision},
            )
            self._last_rejection = rejection
            logger.warning("position_size_zero_after_rounding", symbol=symbol)
            return err(rejection)

        # Enforce minimum notional
        if qty * entry_price < self._min_notional:
            rejection = RiskRejection(
                code="MIN_NOTIONAL_NOT_MET",
                reason="below_min_notional",
                details={
                    "notional": round(qty * entry_price, 2),
                    "min_notional": self._min_notional,
                },
            )
            self._last_rejection = rejection
            logger.warning(
                "below_min_notional",
                symbol=symbol,
                notional=round(qty * entry_price, 2),
                min_notional=self._min_notional,
            )
            return err(rejection)

        # SPEC_043 — Slippage gate (Facade)
        if not self._check_slippage_gate(
            actual_risk_usdt=qty * stop_distance,
            base_risk_usdt=risk_amount,
            symbol=symbol,
            quantity=qty,
            entry_price=entry_price,
            atr_value=0.0,
        ):
            # _check_slippage_gate já setou _last_rejection
            rejection = self._last_rejection
            if rejection is None:
                rejection = RiskRejection(
                    code="SLIPPAGE_EXCEEDS_TOLERANCE",
                    reason="slippage_check_failed",
                    details={},
                )
            return err(rejection)

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

        logger.info("position_size_calculated", **pos.to_dict())
        return ok(pos)

    def _run_pre_trade_gates(
        self,
        *,
        signal: Signal,
        available_balance: float,
        stop_distance: float,
        quantity_precision: int,
        df: pd.DataFrame | None,
    ) -> Result[PositionSize, RiskRejection] | None:
        gates = (self._gate_predictive_circuit_breaker,)
        for gate in gates:
            rejection = gate(
                signal=signal,
                available_balance=available_balance,
                stop_distance=stop_distance,
                quantity_precision=quantity_precision,
                df=df,
            )
            if rejection is not None:
                self._last_rejection = rejection
                return err(rejection)
        return None

    def _gate_predictive_circuit_breaker(
        self,
        *,
        signal: Signal,
        available_balance: float,
        stop_distance: float,
        quantity_precision: int,
        df: pd.DataFrame | None,
    ) -> RiskRejection | None:
        del available_balance, stop_distance, quantity_precision
        if not self._predictive_breaker_enabled:
            return None
        tier = self._liq_map.get(signal.symbol, "medium")
        if tier not in self._predictive_breaker_tiers:
            return None
        if df is None or df.empty or len(df) < self._predictive_breaker_window:
            logger.info(
                "predictive_circuit_breaker_bypassed",
                symbol=signal.symbol,
                reason="insufficient_history",
                required_window=self._predictive_breaker_window,
                received_window=0 if df is None else len(df),
            )
            return None
        if "close" not in df.columns:
            logger.info(
                "predictive_circuit_breaker_bypassed",
                symbol=signal.symbol,
                reason="missing_close_column",
            )
            return None
        close_price = float(df["close"].iloc[-1]) if len(df) > 0 else 0.0
        if close_price <= 0:
            logger.info(
                "predictive_circuit_breaker_bypassed",
                symbol=signal.symbol,
                reason="invalid_close_price",
                close_price=close_price,
            )
            return None
        atr_series = atr_func(df["close"], df["high"], df["low"], self._atr_period)
        atr_ratio_series = (atr_series / df["close"]).tail(self._predictive_breaker_window).dropna()
        if len(atr_ratio_series) < max(2, self._predictive_breaker_window // 2):
            logger.info(
                "predictive_circuit_breaker_bypassed",
                symbol=signal.symbol,
                reason="insufficient_valid_ratio_history",
                valid_points=len(atr_ratio_series),
            )
            return None
        current_ratio = float(atr_ratio_series.iloc[-1])
        should_skip, threshold = self._predictive_breaker_strategy.should_skip(
            current_ratio=current_ratio,
            ratio_history=atr_ratio_series,
            percentile=self._predictive_breaker_percentile,
        )
        if not should_skip:
            return None
        RiskManager._predictive_skips_total += 1
        self._set_rejection(
            code="PREDICTIVE_CIRCUIT_BREAKER_SKIPPED",
            reason="predictive_circuit_breaker_skipped",
            details={
                "tier": tier,
                "atr_ratio": round(current_ratio, 6),
                "threshold": round(threshold, 6),
                "percentile": self._predictive_breaker_percentile,
                "window": self._predictive_breaker_window,
            },
        )
        logger.warning(
            "predictive_circuit_breaker_skipped",
            symbol=signal.symbol,
            tier=tier,
            atr_ratio=round(current_ratio, 6),
            threshold=round(threshold, 6),
            percentile=self._predictive_breaker_percentile,
            window=self._predictive_breaker_window,
            predictive_skips_total=RiskManager._predictive_skips_total,
        )
        return self._last_rejection

    def _estimate_slippage(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        atr_value: float,
    ) -> float:
        """Estima slippage em USDT para o par dado (SPEC_043).

        Usa os tiers de liquidez definidos em _slippage_map (backtest_slippage_by_liq)
        e o mapeamento _liq_map (backtest_slippage_liq_map).

        Se o par não está mapeado, usa default "medium" (0.08%).
        """
        # Proteção contra divisão por zero
        if entry_price <= 0 or quantity <= 0:
            return 0.0

        tier = self._liq_map.get(symbol, "medium")
        slippage_pct = self._slippage_map.get(tier, 0.0008)

        notional = entry_price * quantity
        static_slippage = slippage_pct * notional

        # Slippage dinâmica: 50% do ATR% aplicado ao nocional
        atr_ratio = atr_value / entry_price if atr_value > 0 else 0
        dynamic_slippage = atr_ratio * notional * 0.5

        slippage_usdt = max(static_slippage, dynamic_slippage)

        logger.info(
            "slippage_estimated",
            symbol=symbol,
            tier=tier,
            slippage_pct=slippage_pct,
            notional=round(notional, 4),
            static_slippage=round(static_slippage, 4),
            atr_ratio=round(atr_ratio, 6),
            dynamic_slippage=round(dynamic_slippage, 4),
            slippage_usdt=round(slippage_usdt, 4),
        )
        return slippage_usdt

    def _check_slippage_gate(
        self,
        *,
        actual_risk_usdt: float,
        base_risk_usdt: float,
        symbol: str,
        quantity: float,
        entry_price: float,
        atr_value: float,
    ) -> bool:
        """Facade: valida slippage como fração do risco (SPEC_043).

        Retorna True se o risco total (real + slippage) estiver dentro
        da tolerância configurada. Retorna False e seta _last_rejection
        se exceder.

        A tolerância é reduzida quando o circuit breaker pair-level está
        ativo (_slippage_tolerance_reduced vs _slippage_tolerance_multiplier).
        """
        if not self._slippage_validation_enabled:
            return True

        slippage_estimate = self._estimate_slippage(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            atr_value=atr_value,
        )
        total_risk = actual_risk_usdt + slippage_estimate
        tolerance = (
            self._slippage_tolerance_reduced
            if self._circuit_breaker_active
            else self._slippage_tolerance_multiplier
        )
        # Portfolio CB reduction (Observer)
        if self._get_portfolio_reduction is not None:
            tolerance *= self._get_portfolio_reduction()
        max_allowed = base_risk_usdt * tolerance

        if total_risk > max_allowed:
            self._set_rejection(
                code="SLIPPAGE_EXCEEDS_TOLERANCE",
                reason="slippage_estimate_exceeds_tolerance",
                details={
                    "actual_risk_usdt": round(actual_risk_usdt, 4),
                    "slippage_estimate_usdt": round(slippage_estimate, 4),
                    "total_risk_usdt": round(total_risk, 4),
                    "max_allowed_risk_usdt": round(max_allowed, 4),
                    "tolerance": tolerance,
                    "circuit_breaker_active": self._circuit_breaker_active,
                },
            )
            logger.warning(
                "slippage_exceeds_tolerance",
                symbol=symbol,
                actual_risk_usdt=round(actual_risk_usdt, 4),
                slippage_estimate_usdt=round(slippage_estimate, 4),
                total_risk_usdt=round(total_risk, 4),
                max_allowed_risk_usdt=round(max_allowed, 4),
                tolerance=tolerance,
            )
            return False

        logger.info(
            "slippage_check_passed",
            symbol=symbol,
            actual_risk_usdt=round(actual_risk_usdt, 4),
            slippage_estimate_usdt=round(slippage_estimate, 4),
            total_risk_usdt=round(total_risk, 4),
            max_allowed_risk_usdt=round(max_allowed, 4),
            tolerance=tolerance,
        )
        return True

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

    # ─── SPEC_043 — Circuit Breaker (State Pattern) ──────────────────────────

    @property
    def circuit_breaker_active(self) -> bool:
        """Indica se o circuit breaker pair-level está ativo (risco reduzido)."""
        return self._circuit_breaker_active

    @property
    def effective_risk_per_trade_usdt(self) -> float:
        """Risk_per_trade_usdt ativo — pode estar reduzido pelo CB pair-level + portfólio."""
        risk = self._risk_per_trade_usdt
        if self._get_portfolio_reduction is not None:
            risk *= self._get_portfolio_reduction()
        return risk

    async def register_trade_outcome(self, pnl_usdt: float) -> None:
        """Registra resultado de trade para o circuit breaker (SPEC_043).

        Deve ser chamado pelo TradingMonitor após o fechamento de cada trade.
        Zone morta: PnL entre -0.001 e +0.001 não altera contadores (D10).
        Só executa se circuit_breaker_enabled == True.
        """
        if not self._circuit_breaker_enabled:
            return

        async with self._cb_lock:
            if abs(pnl_usdt) <= DEAD_ZONE:
                return

            if pnl_usdt > 0:
                # Vitória
                if self._circuit_breaker_active:
                    self._recovery_wins_count += 1
                    if self._recovery_wins_count >= self._recovery_wins_needed:
                        # Reset completo
                        self._circuit_breaker_active = False
                        self._consecutive_losses = 0
                        self._recovery_wins_count = 0
                        self._risk_per_trade_usdt = self._original_risk_per_trade_usdt
                        logger.info(
                            "circuit_breaker_reset",
                            reason="recovery_wins_achieved",
                            recovery_wins_needed=self._recovery_wins_needed,
                            restored_risk_usdt=self._risk_per_trade_usdt,
                        )
                else:
                    self._consecutive_losses = 0
            else:
                # Perda
                self._consecutive_losses += 1
                self._recovery_wins_count = 0
                if (
                    self._consecutive_losses >= self._consecutive_loss_threshold
                    and not self._circuit_breaker_active
                ):
                    self._circuit_breaker_active = True
                    reduced_risk = (
                        self._original_risk_per_trade_usdt * self._cb_risk_reduction_factor
                    )
                    self._risk_per_trade_usdt = max(reduced_risk, 1.0)  # INV-043-03: piso $1.00
                    logger.warning(
                        "circuit_breaker_activated",
                        consecutive_losses=self._consecutive_losses,
                        threshold=self._consecutive_loss_threshold,
                        original_risk_usdt=self._original_risk_per_trade_usdt,
                        reduced_risk_usdt=self._risk_per_trade_usdt,
                        reduction_factor=self._cb_risk_reduction_factor,
                    )
