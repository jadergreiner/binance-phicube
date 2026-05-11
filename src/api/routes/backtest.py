"""Rota REST para execução de backtesting (SPEC_011)."""

from __future__ import annotations

import dataclasses
import math
from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)

router = APIRouter()

_VALID_TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w"}


def _serialize(obj: object, _depth: int = 0) -> object:
    if _depth > 5:
        return str(obj)
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        d: dict[str, object] = {}
        for f in dataclasses.fields(obj):  # type: ignore[arg-type]
            v = getattr(obj, f.name)
            if isinstance(v, datetime):
                d[f.name] = v.isoformat().replace("+00:00", "Z")
            elif isinstance(v, list):
                d[f.name] = [_serialize(item, _depth + 1) for item in v]
            elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                d[f.name] = 0.0
            elif dataclasses.is_dataclass(v) and not isinstance(v, type):
                d[f.name] = _serialize(v, _depth + 1)
            else:
                d[f.name] = v
        return d
    return obj


@router.get("/backtest")
async def get_backtest(
    request: Request,
    symbol: Annotated[str, Query(min_length=3, max_length=20)],
    timeframe: Annotated[str, Query()],
    limit: Annotated[int, Query(ge=50, le=60000)] = 500,
    balance: Annotated[float, Query(gt=0)] = 1000.0,
    realistic: Annotated[bool, Query()] = False,
    slippage_override: Annotated[float | None, Query(ge=0)] = None,
) -> JSONResponse:
    """Executa backtest da estratégia Phicube sobre dados históricos.

    Parâmetros:
    - symbol: par negociado (ex: BTCUSDT)
    - timeframe: intervalo de candle (ex: 4h)
    - limit: número de candles a buscar (50–60000, default 500)
    - balance: saldo simulado em USDT (default 1000)
    - realistic: ativa slippage, taxas e sizing real (default false)
    - slippage_override: sobrescreve slippage do tier (gera WARN no log)
    """
    if timeframe not in _VALID_TIMEFRAMES:
        return JSONResponse(
            status_code=422,
            content={"error": "timeframe_invalido", "validos": sorted(_VALID_TIMEFRAMES)},
        )

    try:
        from src.backtest.engine import BacktestEngine
        from src.config.settings import SymbolConfig, get_settings
        from src.exchange.binance_client import BinanceClient
        from src.trading.risk_manager import RiskManager

        settings = get_settings()
        client = BinanceClient(settings)
        await client.connect()
        try:
            if realistic:
                leverage = 3  # default fallback
                for cfg in settings.symbol_timeframes:
                    if isinstance(cfg, SymbolConfig) and cfg.symbol == symbol.upper():
                        leverage = cfg.leverage
                        break
                risk_manager = RiskManager(
                    risk_per_trade_pct=settings.risk_per_trade_pct,
                    leverage=leverage,
                    max_capital_allocation_pct=settings.max_capital_allocation_pct,
                )
                engine = BacktestEngine(settings, client, risk_manager=risk_manager)
            else:
                engine = BacktestEngine(settings, client)

            result = await engine.run(
                symbol.upper(),
                timeframe,
                limit=limit,
                initial_balance=balance,
                realistic=realistic,
                slippage_override=slippage_override,
            )
        finally:
            await client.close()

        return JSONResponse(status_code=200, content=_serialize(result))
    except Exception:
        logger.exception("Erro inesperado no backtest via API")
        return JSONResponse(status_code=503, content={"error": "binance_unavailable"})
