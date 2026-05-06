"""Entry point CLI: python -m src.backtest.runner --symbol BTCUSDT --timeframe 4h --limit 1000"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
from datetime import datetime
from pathlib import Path

from src.backtest.engine import BacktestEngine
from src.config.settings import get_settings
from src.exchange.binance_client import BinanceClient


def _to_dict(result: object) -> object:
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        d = dataclasses.asdict(result)  # type: ignore[arg-type]
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d
    return result


async def _run(symbol: str, timeframe: str, limit: int, balance: float) -> None:
    settings = get_settings()
    client = BinanceClient(settings)
    await client.connect()
    try:
        engine = BacktestEngine(settings, client)
        result = await engine.run(symbol, timeframe, limit=limit, initial_balance=balance)
    finally:
        await client.close()

    print(f"\n=== Backtest {symbol} {timeframe} ({result.candles_used} candles analisados) ===")
    print(f"  Total de trades : {result.total_trades}")
    print(f"  Win rate        : {result.win_rate_pct:.2f}%")
    print(f"  PnL total       : {result.total_pnl_usdt:.4f} USDT")
    print(f"  RRR médio       : {result.avg_rrr:.4f}")
    print(f"  Max drawdown    : {result.max_drawdown_usdt:.4f} USDT")
    print(f"  Profit factor   : {result.profit_factor:.4f}")
    print(f"  Gerado em       : {result.generated_at.isoformat()}")

    out_dir = Path("backtest_results")
    out_dir.mkdir(exist_ok=True)
    ts = result.generated_at.strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"{symbol}_{timeframe}_{ts}.json"
    with open(out_file, "w", encoding="utf-8") as fh:
        json.dump(_to_dict(result), fh, ensure_ascii=False, indent=2, default=str)
    print(f"\nResultado gravado em: {out_file}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Motor de Backtesting Phicube")
    parser.add_argument("--symbol", required=True, help="Par (ex: BTCUSDT)")
    parser.add_argument("--timeframe", required=True, help="Timeframe (ex: 4h)")
    parser.add_argument("--limit", type=int, default=1000, help="Candles a buscar (default: 1000)")
    parser.add_argument("--balance", type=float, default=1000.0, help="Saldo simulado")
    args = parser.parse_args()

    asyncio.run(_run(args.symbol, args.timeframe, args.limit, args.balance))


if __name__ == "__main__":
    main()
