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
class BiasView:
    id: str
    direction: MarketBiasDirection
    confidence: MarketBiasConfidence
    score: float
    reason: str
    metrics: dict[str, float | str | None]


@dataclass(slots=True, frozen=True)
class BiasDivergence:
    has_divergence: bool
    summary: str


@dataclass(slots=True, frozen=True)
class BiasViews:
    active: str
    views: list[BiasView]
    divergence: BiasDivergence


@dataclass(slots=True, frozen=True)
class MarketAnalysis:
    bias: MarketBias
    opportunities: list[TradeOpportunity]
    bias_views: BiasViews


def build_market_analysis(positions: list[PositionView]) -> MarketAnalysis:
    """Analisa o cenário atual das posições abertas e sugere oportunidades."""
    allocation_view = _build_allocation_view(positions)
    pnl_weighted_view = _build_pnl_weighted_view(positions)
    concentration_view = _build_concentration_view(positions)
    bias_views = _build_bias_views([allocation_view, pnl_weighted_view, concentration_view])

    bias = MarketBias(
        direction=allocation_view.direction,
        confidence=allocation_view.confidence,
        score=allocation_view.score,
        reason=allocation_view.reason,
    )
    long_exposure = float(allocation_view.metrics.get("long_exposure") or 0.0)
    short_exposure = float(allocation_view.metrics.get("short_exposure") or 0.0)
    opportunities = _build_opportunities(positions, bias, long_exposure, short_exposure)
    return MarketAnalysis(bias=bias, opportunities=opportunities, bias_views=bias_views)


def _build_allocation_view(positions: list[PositionView]) -> BiasView:
    long_exposure, short_exposure = _compute_exposure_by_side(positions)
    total_exposure = long_exposure + short_exposure
    net_exposure = long_exposure - short_exposure
    relative_balance = abs(net_exposure) / total_exposure if total_exposure > 0 else 0.0
    direction = _resolve_direction_from_net(
        net_exposure=net_exposure, relative_balance=relative_balance
    )
    confidence = _resolve_confidence(relative_balance, direction)
    if total_exposure <= 0:
        reason = "Sem posicoes abertas ou dados insuficientes para definir bias."
    else:
        reason = _build_bias_reason(
            direction=direction,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            relative_balance=relative_balance,
        )
    return BiasView(
        id="allocation",
        direction=direction,
        confidence=confidence,
        score=float(relative_balance),
        reason=reason,
        metrics={
            "long_exposure": long_exposure,
            "short_exposure": short_exposure,
            "relative_balance": relative_balance,
            "net_exposure": net_exposure,
            "total_exposure": total_exposure,
        },
    )


def _build_pnl_weighted_view(positions: list[PositionView]) -> BiasView:
    long_exposure, short_exposure = _compute_exposure_by_side(positions)
    long_pnl = 0.0
    short_pnl = 0.0
    for position in positions:
        pnl = float(getattr(position, "unrealized_pnl_usdt", 0.0) or 0.0)
        side = getattr(position, "side", None)
        if side == "LONG":
            long_pnl += pnl
        elif side == "SHORT":
            short_pnl += pnl

    long_ratio = (long_pnl / long_exposure) if long_exposure > 0 else 0.0
    short_ratio = (short_pnl / short_exposure) if short_exposure > 0 else 0.0
    net_ratio = long_ratio - short_ratio
    score = min(abs(net_ratio), 1.0)
    direction = _resolve_direction_from_net(net_exposure=net_ratio, relative_balance=score)
    confidence = _resolve_confidence(score, direction)
    if direction == "NEUTRAL":
        reason = "PnL ajustado por exposicao sem dominancia clara entre LONG e SHORT."
    else:
        reason = (
            f"PnL ponderado favorece {direction}: LONG={long_ratio:.4f} vs SHORT={short_ratio:.4f}."
        )
    return BiasView(
        id="pnl_weighted",
        direction=direction,
        confidence=confidence,
        score=score,
        reason=reason,
        metrics={
            "long_pnl": long_pnl,
            "short_pnl": short_pnl,
            "long_pnl_ratio": long_ratio,
            "short_pnl_ratio": short_ratio,
            "net_pnl_ratio": net_ratio,
        },
    )


def _build_concentration_view(positions: list[PositionView]) -> BiasView:
    total_exposure = 0.0
    top_symbol = ""
    top_side: MarketBiasDirection = "NEUTRAL"
    top_exposure = 0.0
    for position in positions:
        exposure = _extract_position_exposure(position)
        if exposure is None or exposure <= 0:
            continue
        total_exposure += exposure
        if exposure > top_exposure:
            top_exposure = exposure
            top_symbol = str(getattr(position, "symbol", ""))
            candidate_side = str(getattr(position, "side", "NEUTRAL"))
            top_side = (
                "LONG"
                if candidate_side == "LONG"
                else "SHORT"
                if candidate_side == "SHORT"
                else "NEUTRAL"
            )

    if total_exposure <= 0:
        return BiasView(
            id="concentration",
            direction="NEUTRAL",
            confidence="low",
            score=0.0,
            reason="Sem posicoes abertas para medir concentracao de risco.",
            metrics={
                "top_symbol": None,
                "top_share": 0.0,
                "top_exposure": 0.0,
                "total_exposure": 0.0,
            },
        )

    top_share = top_exposure / total_exposure
    direction = top_side if top_share >= 0.1 else "NEUTRAL"
    confidence = _resolve_confidence(top_share, direction)
    if direction == "NEUTRAL":
        reason = "Concentracao difusa sem simbolo dominante relevante."
    else:
        reason = (
            f"Concentracao em {top_symbol}: {top_share:.0%} da exposicao total no lado {direction}."
        )
    return BiasView(
        id="concentration",
        direction=direction,
        confidence=confidence,
        score=top_share,
        reason=reason,
        metrics={
            "top_symbol": top_symbol or None,
            "top_share": top_share,
            "top_exposure": top_exposure,
            "total_exposure": total_exposure,
        },
    )


def _build_bias_views(views: list[BiasView]) -> BiasViews:
    unique_directions = {view.direction for view in views}
    has_divergence = len(unique_directions) > 1
    if has_divergence:
        summary = " ; ".join(f"{view.id}={view.direction}" for view in views)
    else:
        summary = f"Sem divergencia: todas as visoes em {views[0].direction}."
    return BiasViews(
        active="allocation",
        views=views,
        divergence=BiasDivergence(has_divergence=has_divergence, summary=summary),
    )


def _resolve_direction_from_net(
    *, net_exposure: float, relative_balance: float
) -> MarketBiasDirection:
    if net_exposure > 0 and relative_balance >= 0.1:
        return "LONG"
    if net_exposure < 0 and relative_balance >= 0.1:
        return "SHORT"
    return "NEUTRAL"


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


def _resolve_confidence(
    relative_balance: float, direction: MarketBiasDirection
) -> MarketBiasConfidence:
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
            "Exposicao balanceada entre LONG e SHORT; o mercado nao apresenta "
            "bias claro no momento."
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
                    "Exposicao balanceada; aguarde confirmacao adicional antes de "
                    "abrir novas posicoes."
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
                        "O mercado favorece LONG e esta posicao possui a maior "
                        "exposicao LONG atual. Considere reforcar a tendencia ou manter a posicao."
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
                        "Bias LONG dominante. Considere reduzir exposicao SHORT para "
                        "alinhar o portifolio."
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
                        "O mercado favorece SHORT e esta posicao possui a maior "
                        "exposicao SHORT atual. Considere reforcar a tendencia ou manter a posicao."
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
                        "Bias SHORT dominante. Considere reduzir exposicao LONG para "
                        "alinhar o portifolio."
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
                    "Nenhuma oportunidade especifica identificada. Mantenha a disciplina e "
                    "aguarde nova confirmacao."
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
