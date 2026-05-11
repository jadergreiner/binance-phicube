"""Entry point CLI: python -m src.backtest.runner --symbol BTCUSDT --timeframe 4h --limit 1000"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
from datetime import datetime
from pathlib import Path

from src.backtest.engine import BacktestEngine
from src.config.settings import SymbolConfig, get_settings
from src.exchange.binance_client import BinanceClient
from src.monitoring.logger import get_logger
from src.trading.risk_manager import RiskManager

logger = get_logger(__name__)

_VALID_TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w"}


def _to_dict(result: object, _depth: int = 0) -> object:
    if _depth > 5:
        return repr(result)
    if isinstance(result, list):
        return [_to_dict(item, _depth + 1) for item in result]
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        d: dict[str, object] = {}
        for f in dataclasses.fields(result):  # type: ignore[arg-type]
            v = _to_dict(getattr(result, f.name), _depth + 1)
            if isinstance(v, datetime):
                v = v.isoformat()
            d[f.name] = v
        return d
    return result


async def _run(
    symbol: str,
    timeframe: str,
    limit: int,
    balance: float,
    realistic: bool = False,
    slippage_override: float | None = None,
) -> None:
    if slippage_override is not None:
        logger.warning(
            "override-slippage ativo — resultado pode não refletir liquidez real do par",
            symbol=symbol,
            override_value=slippage_override,
        )

    settings = get_settings()
    client = BinanceClient(settings)
    await client.connect()
    try:
        if realistic:
            # Find leverage for this symbol from settings
            leverage = 3  # default fallback
            for cfg in settings.symbol_timeframes:
                if isinstance(cfg, SymbolConfig) and cfg.symbol == symbol:
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
            symbol,
            timeframe,
            limit=limit,
            initial_balance=balance,
            realistic=realistic,
            slippage_override=slippage_override,
        )
    finally:
        await client.close()

    mode_label = "Realista" if realistic else "Simples"
    print(f"\n=== Backtest {mode_label}: {symbol} {timeframe} ({result.candles_used} candles) ===")
    print(f"  Total de trades : {result.total_trades}")
    print(f"  Win rate        : {result.win_rate_pct:.2f}%")
    print(f"  PnL total       : {result.total_pnl_usdt:.4f} USDT")
    print(f"  RRR médio       : {result.avg_rrr:.4f}")
    print(f"  Max drawdown    : {result.max_drawdown_usdt:.4f} USDT")
    print(f"  Profit factor   : {result.profit_factor:.4f}")

    if realistic and result.gross is not None:
        gross = result.gross
        print("  ─────────────────────────────────────")
        print(f"  Gross PnL       : {gross.total_pnl_usdt:.4f} USDT (sem custos)")
        print(f"  Net PnL         : {result.total_pnl_usdt:.4f} USDT (com custos)")
        print(f"  Total taxas     : {result.total_fees_usdt:.4f} USDT")
        print(f"  Total slippage  : {result.total_slippage_usdt:.4f} USDT")

        if result.warnings:
            print("\n  ⚠️  Análise de Confiabilidade:")
            for w in result.warnings:
                print(f"    • {w}")

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
    parser.add_argument(
        "--realistic", action="store_true", help="Ativa slippage, taxas e sizing real"
    )
    parser.add_argument(
        "--override-slippage",
        type=float,
        default=None,
        help="Sobrescreve slippage do tier (gera WARN no log)",
    )
    args = parser.parse_args()

    if args.timeframe not in _VALID_TIMEFRAMES:
        print(f"Erro: timeframe inválido '{args.timeframe}'. Válidos: {sorted(_VALID_TIMEFRAMES)}")
        return

    asyncio.run(
        _run(
            args.symbol,
            args.timeframe,
            args.limit,
            args.balance,
            realistic=args.realistic,
            slippage_override=args.override_slippage,
        )
    )


if __name__ == "__main__":
    main()
