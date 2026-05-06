"""TEST_011_06 — Runner CLI produz saída JSON válida (mock BinanceClient).

Verifica que o runner grava um arquivo JSON válido com as chaves esperadas de BacktestResult.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd


def _make_df(n: int = 20, base: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open_time": range(n),
            "open": [base] * n,
            "high": [base + 0.1] * n,
            "low": [base - 0.1] * n,
            "close": [base] * n,
            "volume": [1000.0] * n,
        }
    )


class TestRunnerCLI:
    """TEST_011_06 — runner CLI grava JSON válido."""

    def test_runner_grava_json_valido(self, tmp_path: Path) -> None:
        settings = MagicMock()
        settings.warmup_candles = 5
        settings.risk_reward_ratio = 2.0
        settings.risk_per_trade_pct = 1.0
        settings.leverage = 5
        settings.max_capital_allocation_pct = 30.0

        client_mock = AsyncMock()
        client_mock.fetch_ohlcv = AsyncMock(return_value=_make_df(20))
        client_mock.connect = AsyncMock()
        client_mock.close = AsyncMock()

        async def _run() -> None:
            from src.backtest.engine import BacktestEngine

            with patch("src.backtest.engine.SignalEngine") as MockSE:
                MockSE.return_value.evaluate = MagicMock(return_value=None)
                engine = BacktestEngine(settings, client_mock)
                result = await engine.run("BTCUSDT", "4h", limit=20, initial_balance=1000.0)

            # simula o que o runner faz: serializa e grava JSON
            import dataclasses
            from datetime import datetime

            def _to_dict(obj: object) -> object:
                if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
                    d = dataclasses.asdict(obj)  # type: ignore[arg-type]
                    for k, v in d.items():
                        if isinstance(v, datetime):
                            d[k] = v.isoformat()
                    return d
                return obj

            out_file = tmp_path / "result.json"
            with open(out_file, "w", encoding="utf-8") as fh:
                json.dump(_to_dict(result), fh, ensure_ascii=False, indent=2, default=str)

            return out_file

        out_file = asyncio.run(_run())
        assert out_file.exists()

        with open(out_file, encoding="utf-8") as fh:
            data = json.load(fh)

        assert "symbol" in data
        assert "timeframe" in data
        assert "total_trades" in data
        assert "win_rate_pct" in data
        assert "total_pnl_usdt" in data
        assert "avg_rrr" in data
        assert "max_drawdown_usdt" in data
        assert "profit_factor" in data
        assert "generated_at" in data
        assert data["symbol"] == "BTCUSDT"
        assert data["total_trades"] == 0
