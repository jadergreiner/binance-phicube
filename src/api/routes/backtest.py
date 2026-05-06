"""Rota REST para execução de backtesting (SPEC_011)."""

from __future__ import annotations

import dataclasses
import math
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter()

_VALID_TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w"}


def _serialize(obj: object) -> object:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        d = {}
        for f in dataclasses.fields(obj):  # type: ignore[arg-type]
            v = getattr(obj, f.name)
            if isinstance(v, datetime):
                d[f.name] = v.isoformat().replace("+00:00", "Z")
            elif isinstance(v, list):
                d[f.name] = [_serialize(item) for item in v]
            elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                d[f.name] = 0.0
            else:
                d[f.name] = v
        return d
    return obj


@router.get("/backtest")
async def get_backtest(
    request: Request,
    symbol: Annotated[str, Query(min_length=3, max_length=20)],
    timeframe: Annotated[str, Query()],
    limit: Annotated[int, Query(ge=50, le=5000)] = 500,
    balance: Annotated[float, Query(gt=0)] = 1000.0,
) -> JSONResponse:
    """Executa backtest da estratégia Phicube sobre dados históricos.

    Parâmetros:
    - symbol: par negociado (ex: BTCUSDT)
    - timeframe: intervalo de candle (ex: 4h)
    - limit: número de candles a buscar (50–5000, default 500)
    - balance: saldo simulado em USDT (default 1000)
    """
    if timeframe not in _VALID_TIMEFRAMES:
        return JSONResponse(
            status_code=422,
            content={"error": "timeframe_invalido", "validos": sorted(_VALID_TIMEFRAMES)},
        )

    try:
        from src.backtest.engine import BacktestEngine
        from src.config.settings import get_settings
        from src.exchange.binance_client import BinanceClient

        settings = get_settings()
        client = BinanceClient(settings)
        await client.connect()
        try:
            engine = BacktestEngine(settings, client)
            result = await engine.run(
                symbol.upper(), timeframe, limit=limit, initial_balance=balance
            )
        finally:
            await client.close()

        return JSONResponse(status_code=200, content=_serialize(result))
    except Exception:
        return JSONResponse(status_code=503, content={"error": "binance_unavailable"})
