"""Rotas de visão operacional por símbolo (P0)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.api.datetime_utils import BRAZIL_TIMEZONE, enrich_datetime_fields, to_brazil_datetime_str

router = APIRouter()

_CRITICAL_CLASSIFICATIONS = {
    "PIPELINE_INTERRUPTED",
}


def _classify_risk_status(
    *,
    classification: str | None,
    risk_reason: str | None,
    last_evidence_at: datetime | None,
    stale_limit_minutes: int = 20,
) -> tuple[str, list[str]]:
    flags: list[str] = []
    normalized = (classification or "").upper()
    if normalized in _CRITICAL_CLASSIFICATIONS:
        flags.append("pipeline_interrupted")
    if normalized.startswith("REJECTED_"):
        flags.append("rejected_signal")
    if risk_reason:
        flags.append(f"risk_reason:{risk_reason}")

    if last_evidence_at is None:
        flags.append("missing_evidence")
    else:
        now = datetime.now(UTC)
        if (now - last_evidence_at.astimezone(UTC)) > timedelta(minutes=stale_limit_minutes):
            flags.append("stale_data")

    if any(flag in {"pipeline_interrupted", "missing_evidence"} for flag in flags):
        return "bloqueado", flags
    if flags:
        return "atencao", flags
    return "ok", flags


def _build_human_explanation(diagnosis: dict[str, Any]) -> dict[str, str]:
    classification = str(diagnosis.get("classification") or "UNKNOWN").upper()
    reason = str(
        diagnosis.get("risk_reason")
        or diagnosis.get("engine_reason")
        or diagnosis.get("engine_outcome")
        or ""
    ).strip()
    if classification == "SIGNAL_GENERATED":
        text = {
            "what_i_saw": "Eu vi um cenário com chance de entrada.",
            "what_i_decided": "Decidi sinalizar uma possível operação.",
            "why": "As condições mínimas ficaram alinhadas para tentar entrada.",
            "next_step": "Agora o sistema confirma risco e execução antes de abrir posição.",
        }
    elif classification == "NO_SETUP_DETECTED":
        text = {
            "what_i_saw": "Eu vi o preço sem um padrão claro para operar.",
            "what_i_decided": "Decidi não abrir operação agora.",
            "why": "Quando o cenário está confuso, operar aumenta o risco.",
            "next_step": "Vou esperar uma configuração mais clara para reavaliar.",
        }
    elif classification.startswith("REJECTED_"):
        text = {
            "what_i_saw": "Eu vi uma chance, mas havia risco operacional para continuar.",
            "what_i_decided": "Decidi bloquear a execução desta entrada.",
            "why": f"O principal motivo foi: {reason or 'restrição de risco'}.",
            "next_step": "Aguardarei condições seguras antes de tentar novamente.",
        }
    else:
        text = {
            "what_i_saw": "Eu coletei os dados mais recentes do símbolo.",
            "what_i_decided": "Não há decisão operacional confirmada neste momento.",
            "why": f"A classificação atual é {classification}.",
            "next_step": "Seguirei monitorando até surgir um contexto mais claro.",
        }
    text["full_text"] = (
        f"{text['what_i_saw']} {text['what_i_decided']} {text['why']} {text['next_step']}"
    )
    return text


def _build_trader_technical_explanation(diagnosis: dict[str, Any]) -> dict[str, str]:
    """Gera explicação técnica estruturada para leitura operacional de trader."""
    details = diagnosis.get("details") if isinstance(diagnosis.get("details"), dict) else {}
    details = details or {}

    ma_state = details.get("ma_state") or details.get("moving_average_state") or "não informado"
    above_ma = details.get("price_above_ma") or details.get("price_above_moving_averages")
    ma_cross = details.get("ma_cross") or details.get("moving_average_cross")
    trend = details.get("trend") or details.get("market_trend") or "não informado"
    ao_state = details.get("ao_state") or details.get("awesome_oscillator_state") or "não informado"
    stoch_state = details.get("stochastic_state") or details.get("stoch_state") or "não informado"
    fractal_state = details.get("fractal_state") or details.get("fractals_state") or "não informado"

    ma_parts = [str(ma_state)]
    if isinstance(above_ma, bool):
        ma_parts.append("acima das médias" if above_ma else "abaixo das médias")
    if ma_cross:
        ma_parts.append(f"cruzamento: {ma_cross}")

    structured = {
        "tendencia": str(trend),
        "medias": "; ".join(ma_parts),
        "momentum": str(ao_state),
        "oscilador": str(stoch_state),
        "fractal": str(fractal_state),
    }

    if any(
        value != "não informado" and "não informado" not in value
        for value in structured.values()
    ):
        return structured

    classification = str(diagnosis.get("classification") or "UNKNOWN").upper()
    engine_outcome = str(diagnosis.get("engine_outcome") or "").strip()
    fallback = (
        "Indicadores técnicos detalhados não vieram enriquecidos nesta leitura. "
        f"Classificação: {classification}. "
        f"Estado do motor: {engine_outcome or 'não informado'}."
    )
    return {
        "tendencia": "não informado",
        "medias": "não informado",
        "momentum": "não informado",
        "oscilador": "não informado",
        "fractal": "não informado",
        "fallback": fallback,
    }


def _build_watch_zones(
    trades: list[dict[str, Any]], current_price: float | None
) -> list[dict[str, Any]]:
    if not trades:
        return []
    latest = trades[0]
    zones: list[dict[str, Any]] = []
    entry = latest.get("entry_price")
    sl = latest.get("stop_loss")
    tp = latest.get("take_profit")
    if isinstance(entry, (int, float)):
        zones.append(
            {
                "zone_id": "entrada",
                "type": "entrada",
                "price_min": float(entry),
                "price_max": float(entry),
                "priority": "high",
                "why_human": "Esta é a região base usada como referência de entrada.",
                "expected_action": "watch",
            }
        )
    if isinstance(sl, (int, float)):
        zones.append(
            {
                "zone_id": "invalidacao",
                "type": "invalidacao",
                "price_min": float(sl),
                "price_max": float(sl),
                "priority": "high",
                "why_human": "Se o preço perder este nível, o cenário é invalidado.",
                "expected_action": "avoid",
            }
        )
    if isinstance(tp, (int, float)):
        zones.append(
            {
                "zone_id": "alvo",
                "type": "alvo",
                "price_min": float(tp),
                "price_max": float(tp),
                "priority": "medium",
                "why_human": "Esta é a região de objetivo principal da operação.",
                "expected_action": "watch",
            }
        )
    if current_price is not None:
        zones.append(
            {
                "zone_id": "observacao",
                "type": "observacao",
                "price_min": current_price,
                "price_max": current_price,
                "priority": "low",
                "why_human": "Este é o preço atual para acompanhar aproximação das zonas.",
                "expected_action": "watch",
            }
        )
    return zones


@router.get("/symbols/overview")
async def get_symbols_overview(request: Request) -> JSONResponse:
    """Lista símbolos monitorados com resumo operacional mínimo (P0)."""
    settings = getattr(request.app.state, "settings", None)
    repo = getattr(request.app.state, "repository", None)
    if settings is None or repo is None:
        return JSONResponse(status_code=503, content={"detail": "Dependências indisponíveis"})

    rows: list[dict[str, Any]] = []
    for cfg in settings.symbol_timeframes:
        diagnosis = await repo.get_signal_generation_diagnosis(cfg.symbol, cfg.timeframe)
        evidence = diagnosis.get("last_evidence_at")
        risk_status, risk_flags = _classify_risk_status(
            classification=diagnosis.get("classification"),
            risk_reason=diagnosis.get("risk_reason"),
            last_evidence_at=evidence,
        )
        rows.append(
            {
                "symbol": cfg.symbol,
                "timeframe": cfg.timeframe,
                "last_analysis_summary": diagnosis.get("classification"),
                "momentum_summary": diagnosis.get("engine_outcome"),
                "current_price": None,
                "period_pnl": None,
                "risk_status": risk_status,
                "risk_flags": risk_flags,
                "as_of": datetime.now(UTC),
            }
        )

    generated_at = datetime.now(UTC)
    payload = {
        "symbols": rows,
        "total": len(rows),
        "generated_at": generated_at,
        "generated_at_br": to_brazil_datetime_str(generated_at),
        "timezone": BRAZIL_TIMEZONE,
    }
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@router.get("/symbols/{symbol}/detail")
async def get_symbol_detail(request: Request, symbol: str, timeframe: str = "15m") -> JSONResponse:
    """Facade de detalhe operacional por símbolo (P0)."""
    repo = getattr(request.app.state, "repository", None)
    stream = getattr(request.app.state, "position_stream", None)
    if repo is None:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    normalized_symbol = symbol.upper()
    diagnosis = await repo.get_signal_generation_diagnosis(normalized_symbol, timeframe)
    diagnosis = enrich_datetime_fields(diagnosis, ("last_evidence_at",))
    evidence_at = diagnosis.get("last_evidence_at")
    evidence_dt = None
    if isinstance(evidence_at, str):
        try:
            evidence_dt = datetime.fromisoformat(evidence_at.replace("Z", "+00:00"))
        except ValueError:
            evidence_dt = None

    risk_status, risk_flags = _classify_risk_status(
        classification=diagnosis.get("classification"),
        risk_reason=diagnosis.get("risk_reason"),
        last_evidence_at=evidence_dt,
    )
    human = _build_human_explanation(diagnosis)

    closed_trades = await repo.get_trade_history(limit=200)
    symbol_trades = [
        t for t in closed_trades if str(t.get("symbol", "")).upper() == normalized_symbol
    ]
    symbol_trades = [enrich_datetime_fields(t, ("opened_at", "closed_at")) for t in symbol_trades]

    current_price = None
    if stream is not None:
        try:
            positions = list(stream.get_positions())
            pos = next(
                (
                    p
                    for p in positions
                    if str(getattr(p, "symbol", "")).upper() == normalized_symbol
                ),
                None,
            )
            if pos is not None:
                mark = getattr(pos, "mark_price", None)
                if mark is not None:
                    current_price = float(mark)
        except Exception:
            current_price = None

    zones = _build_watch_zones(symbol_trades, current_price)
    technical = _build_trader_technical_explanation(diagnosis)
    now = datetime.now(UTC)
    payload = {
        "symbol": normalized_symbol,
        "timeframe": timeframe,
        "as_of": now,
        "snapshot": {
            "symbol": normalized_symbol,
            "timeframe": timeframe,
            "current_price": current_price,
            "as_of": now,
        },
        "risk": {
            "risk_status": risk_status,
            "risk_flags": risk_flags,
            "as_of": now,
        },
        "last_analysis": {
            **diagnosis,
            "human_explanation": human,
            "technical_explanation": technical.get("fallback") or (
                f"Tendência: {technical.get('tendencia', 'não informado')}. "
                f"Médias: {technical.get('medias', 'não informado')}. "
                f"Momentum: {technical.get('momentum', 'não informado')}. "
                f"Oscilador: {technical.get('oscilador', 'não informado')}. "
                f"Fractal: {technical.get('fractal', 'não informado')}."
            ),
            "technical_explanation_structured": technical,
            "as_of": now,
        },
        "chart": {
            "current_price": current_price,
            "candles": [],
            "levels": {
                "entry": symbol_trades[0].get("entry_price") if symbol_trades else None,
                "sl": symbol_trades[0].get("stop_loss") if symbol_trades else None,
                "tp": symbol_trades[0].get("take_profit") if symbol_trades else None,
            },
            "watch_zones": zones,
            "as_of": now,
        },
        "trades_history": {
            "items": symbol_trades[:50],
            "total": len(symbol_trades),
            "as_of": now,
        },
    }
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))
