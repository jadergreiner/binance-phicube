"""Análise de cenário de mercado com base nas posições abertas do dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.dashboard.models import PositionView

MarketBiasDirection = Literal["LONG", "SHORT", "NEUTRAL"]
MarketBiasConfidence = Literal["high", "medium", "low"]
MarketOpportunityAction = Literal["ADD", "REDUCE", "HOLD"]


@dataclass(slots=True, frozen=True)
class MarketBias:
    direction: MarketBiasDirection
    confidence: MarketBiasConfidence
    score: float
    reason: str


@dataclass(slots=True, frozen=True)
class TradeOpportunity:
    symbol: str | None
    direction: MarketBiasDirection
    action: MarketOpportunityAction
    rationale: str
    exposure_usdt: float | None = None


@dataclass(slots=True, frozen=True)
class MarketAnalysis:
    bias: MarketBias
    opportunities: list[TradeOpportunity]


def build_market_analysis(positions: list[PositionView]) -> MarketAnalysis:
    """Analisa o cenário atual das posições abertas e sugere oportunidades."""
    long_exposure, short_exposure = _compute_exposure_by_side(positions)
    total_exposure = long_exposure + short_exposure
    net_exposure = long_exposure - short_exposure

    if total_exposure <= 0:
        bias = MarketBias(
            direction="NEUTRAL",
            confidence="low",
            score=0.0,
            reason="Sem posicoes abertas ou dados insuficientes para definir bias.",
        )
        opportunities = [
            TradeOpportunity(
                symbol=None,
                direction="NEUTRAL",
                action="HOLD",
                rationale=(
                    "Nenhuma oportunidade definida: o painel nao apresenta posicoes abertas "
                    "para gerar bias de mercado."
                ),
                exposure_usdt=None,
            )
        ]
        return MarketAnalysis(bias=bias, opportunities=opportunities)

    relative_balance = abs(net_exposure) / total_exposure
    direction = (
        "LONG"
        if net_exposure > 0 and relative_balance >= 0.1
        else "SHORT"
        if net_exposure < 0 and relative_balance >= 0.1
        else "NEUTRAL"
    )

    confidence = _resolve_confidence(relative_balance, direction)
    score = float(abs(net_exposure) / total_exposure)
    reason = _build_bias_reason(
        direction=direction,
        long_exposure=long_exposure,
        short_exposure=short_exposure,
        relative_balance=relative_balance,
    )

    bias = MarketBias(direction=direction, confidence=confidence, score=score, reason=reason)
    opportunities = _build_opportunities(positions, bias, long_exposure, short_exposure)
    return MarketAnalysis(bias=bias, opportunities=opportunities)


def _compute_exposure_by_side(positions: list[PositionView]) -> tuple[float, float]:
    long_exposure = 0.0
    short_exposure = 0.0
    for position in positions:
        exposure = _extract_position_exposure(position)
        if exposure is None or exposure <= 0:
            continue

        if getattr(position, "side", None) == "LONG":
            long_exposure += exposure
        elif getattr(position, "side", None) == "SHORT":
            short_exposure += exposure
    return long_exposure, short_exposure


def _extract_position_exposure(position: object) -> float | None:
    exposure = getattr(position, "position_size_usdt", None)
    if exposure is not None:
        return float(exposure)

    margin = getattr(position, "margin_used_usdt", None)
    leverage = getattr(position, "leverage", None)
    try:
        if margin is not None and leverage is not None:
            margin_value = float(margin)
            leverage_value = int(leverage)
            if margin_value >= 0 and leverage_value > 0:
                return margin_value * leverage_value
    except Exception:
        return None

    return None


def _resolve_confidence(relative_balance: float, direction: MarketBiasDirection) -> MarketBiasConfidence:
    if direction == "NEUTRAL":
        return "low"
    if relative_balance >= 0.6:
        return "high"
    if relative_balance >= 0.3:
        return "medium"
    return "low"


def _build_bias_reason(
    *,
    direction: MarketBiasDirection,
    long_exposure: float,
    short_exposure: float,
    relative_balance: float,
) -> str:
    if direction == "NEUTRAL":
        return (
            "Exposicao balanceada entre LONG e SHORT; o mercado nao apresenta bias claro no momento."
        )

    dominant = "LONG" if direction == "LONG" else "SHORT"
    smaller = short_exposure if direction == "LONG" else long_exposure
    return (
        f"Bias {dominant}: exposicao {dominant} de {max(long_exposure, short_exposure):.2f} "
        f"contra {smaller:.2f} do lado oposto. "
        f"Forca do bias: {relative_balance:.0%}."
    )


def _build_opportunities(
    positions: list[PositionView],
    bias: MarketBias,
    long_exposure: float,
    short_exposure: float,
) -> list[TradeOpportunity]:
    if bias.direction == "NEUTRAL":
        return [
            TradeOpportunity(
                symbol=None,
                direction="NEUTRAL",
                action="HOLD",
                rationale=(
                    "Exposicao balanceada; aguarde confirmacao adicional antes de abrir novas posicoes."
                ),
                exposure_usdt=None,
            )
        ]

    opportunities: list[TradeOpportunity] = []
    if bias.direction == "LONG":
        top_long = _top_position_by_exposure(positions, "LONG")
        top_short = _top_position_by_exposure(positions, "SHORT")
        if top_long is not None:
            opportunities.append(
                TradeOpportunity(
                    symbol=top_long.symbol,
                    direction="LONG",
                    action="ADD",
                    rationale=(
                        "O mercado favorece LONG e esta posicao possui a maior exposicao LONG atual. "
                        "Considere reforcar a tendencia ou manter a posicao."
                    ),
                    exposure_usdt=_extract_position_exposure(top_long),
                )
            )
        if top_short is not None:
            opportunities.append(
                TradeOpportunity(
                    symbol=top_short.symbol,
                    direction="SHORT",
                    action="REDUCE",
                    rationale=(
                        "Bias LONG dominante. Considere reduzir exposicao SHORT para alinhar o portifolio."
                    ),
                    exposure_usdt=_extract_position_exposure(top_short),
                )
            )
    else:
        top_short = _top_position_by_exposure(positions, "SHORT")
        top_long = _top_position_by_exposure(positions, "LONG")
        if top_short is not None:
            opportunities.append(
                TradeOpportunity(
                    symbol=top_short.symbol,
                    direction="SHORT",
                    action="ADD",
                    rationale=(
                        "O mercado favorece SHORT e esta posicao possui a maior exposicao SHORT atual. "
                        "Considere reforcar a tendencia ou manter a posicao."
                    ),
                    exposure_usdt=_extract_position_exposure(top_short),
                )
            )
        if top_long is not None:
            opportunities.append(
                TradeOpportunity(
                    symbol=top_long.symbol,
                    direction="LONG",
                    action="REDUCE",
                    rationale=(
                        "Bias SHORT dominante. Considere reduzir exposicao LONG para alinhar o portifolio."
                    ),
                    exposure_usdt=_extract_position_exposure(top_long),
                )
            )

    if not opportunities:
        opportunities.append(
            TradeOpportunity(
                symbol=None,
                direction=bias.direction,
                action="HOLD",
                rationale=(
                    "Nenhuma oportunidade especifica identificada. Mantenha a disciplina e aguarde nova confirmacao."
                ),
                exposure_usdt=None,
            )
        )
    return opportunities


def _top_position_by_exposure(
    positions: list[PositionView],
    side: str,
) -> PositionView | None:
    candidates = []
    for position in positions:
        if getattr(position, "side", None) != side:
            continue
        exposure = _extract_position_exposure(position)
        if exposure is None or exposure <= 0:
            continue
        candidates.append((position, exposure))

    if not candidates:
        return None

    top_position, _ = max(candidates, key=lambda item: item[1])
    return top_position
