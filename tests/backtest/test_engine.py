"""Testes unitários do BacktestEngine (SPEC_011).

TEST_011_01: sem trades → result vazio (métricas zeradas)
TEST_011_02: 1 trade TP → win_rate=100%, pnl > 0
TEST_011_03: 1 trade SL → win_rate=0%, pnl < 0
TEST_011_04: warmup respeitado — candles antes do warmup não geram trades
TEST_011_05: max_drawdown calculado corretamente (pior pico→vale)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.backtest.engine import BacktestEngine
from src.backtest.models import BacktestResult


def _make_settings(warmup: int = 5, rrr: float = 2.0) -> MagicMock:
    s = MagicMock()
    s.warmup_candles = warmup
    s.risk_reward_ratio = rrr
    s.risk_per_trade_pct = 1.0
    s.leverage = 5
    s.max_capital_allocation_pct = 30.0
    return s


def _make_df(n: int, base_price: float = 100.0) -> pd.DataFrame:
    """DataFrame sintético de n candles sem nenhum sinal BO Williams válido."""
    return pd.DataFrame(
        {
            "open_time": range(n),
            "open": [base_price] * n,
            "high": [base_price + 0.1] * n,
            "low": [base_price - 0.1] * n,
            "close": [base_price] * n,
            "volume": [1000.0] * n,
        }
    )


def _make_signal(
    direction: str = "LONG", entry: float = 100.0, sl: float = 95.0, tp: float = 110.0
) -> MagicMock:
    sig = MagicMock()
    sig.direction = MagicMock()
    sig.direction.value = direction
    sig.entry_price = entry
    sig.stop_loss = sl
    sig.take_profit = tp
    return sig


class TestBacktestEngineSemTrades:
    """TEST_011_01 — sem trades → resultado vazio."""

    @pytest.mark.asyncio
    async def test_sem_trades_retorna_result_vazio(self) -> None:
        settings = _make_settings(warmup=5)
        client = AsyncMock()
        client.fetch_ohlcv = AsyncMock(return_value=_make_df(10))

        with patch("src.backtest.engine.SignalEngine") as MockSE:
            MockSE.return_value.evaluate = MagicMock(return_value=None)
            engine = BacktestEngine(settings, client)
            result = await engine.run("BTCUSDT", "4h", limit=10)

        assert isinstance(result, BacktestResult)
        assert result.total_trades == 0
        assert result.win_rate_pct == 0.0
        assert result.total_pnl_usdt == 0.0
        assert result.trades == []


class TestBacktestEngineTradeTP:
    """TEST_011_02 — 1 trade TP → win_rate=100%, pnl > 0."""

    @pytest.mark.asyncio
    async def test_trade_tp_win_rate_100(self) -> None:
        settings = _make_settings(warmup=3)
        base = 100.0
        sl = 95.0
        tp = 110.0

        # candles: 10 de base, depois 1 com high >= tp para fechar TP
        rows = []
        for i in range(10):
            rows.append(
                {
                    "open_time": i,
                    "open": base,
                    "high": base + 0.1,
                    "low": base - 0.1,
                    "close": base,
                    "volume": 1000.0,
                }
            )
        # candle de fechamento: high >= tp
        rows.append(
            {
                "open_time": 10,
                "open": base,
                "high": tp + 1,
                "low": base - 0.1,
                "close": tp,
                "volume": 1000.0,
            }
        )
        df = pd.DataFrame(rows)

        client = AsyncMock()
        client.fetch_ohlcv = AsyncMock(return_value=df)

        signal = _make_signal("LONG", entry=base, sl=sl, tp=tp)
        call_count = 0

        def _evaluate(sym, tf, window):
            nonlocal call_count
            call_count += 1
            # sinal apenas no primeiro candle elegível (warmup=3, então candle índice 3)
            if call_count == 1:
                return signal
            return None

        with patch("src.backtest.engine.SignalEngine") as MockSE:
            MockSE.return_value.evaluate = MagicMock(side_effect=_evaluate)
            engine = BacktestEngine(settings, client)
            result = await engine.run("BTCUSDT", "4h", limit=20, initial_balance=1000.0)

        assert result.total_trades == 1
        assert result.win_rate_pct == 100.0
        assert result.total_pnl_usdt > 0
        assert result.trades[0].close_reason == "TP"


class TestBacktestEngineTradeSL:
    """TEST_011_03 — 1 trade SL → win_rate=0%, pnl < 0."""

    @pytest.mark.asyncio
    async def test_trade_sl_win_rate_zero(self) -> None:
        settings = _make_settings(warmup=3)
        base = 100.0
        sl = 95.0
        tp = 110.0

        rows = []
        for i in range(10):
            rows.append(
                {
                    "open_time": i,
                    "open": base,
                    "high": base + 0.1,
                    "low": base - 0.1,
                    "close": base,
                    "volume": 1000.0,
                }
            )
        # candle de fechamento: low <= sl
        rows.append(
            {
                "open_time": 10,
                "open": base,
                "high": base + 0.1,
                "low": sl - 1,
                "close": sl,
                "volume": 1000.0,
            }
        )
        df = pd.DataFrame(rows)

        client = AsyncMock()
        client.fetch_ohlcv = AsyncMock(return_value=df)

        signal = _make_signal("LONG", entry=base, sl=sl, tp=tp)
        call_count = 0

        def _evaluate(sym, tf, window):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return signal
            return None

        with patch("src.backtest.engine.SignalEngine") as MockSE:
            MockSE.return_value.evaluate = MagicMock(side_effect=_evaluate)
            engine = BacktestEngine(settings, client)
            result = await engine.run("BTCUSDT", "4h", limit=20, initial_balance=1000.0)

        assert result.total_trades == 1
        assert result.win_rate_pct == 0.0
        assert result.total_pnl_usdt < 0
        assert result.trades[0].close_reason == "SL"


class TestBacktestEngineWarmup:
    """TEST_011_04 — warmup respeitado: candles anteriores não geram trades."""

    @pytest.mark.asyncio
    async def test_warmup_nao_gera_trades(self) -> None:
        settings = _make_settings(warmup=10)
        df = _make_df(10)  # exatamente warmup candles — nenhum elegível

        client = AsyncMock()
        client.fetch_ohlcv = AsyncMock(return_value=df)

        evaluate_called = False

        def _evaluate(sym, tf, window):
            nonlocal evaluate_called
            evaluate_called = True
            return _make_signal()

        with patch("src.backtest.engine.SignalEngine") as MockSE:
            MockSE.return_value.evaluate = MagicMock(side_effect=_evaluate)
            engine = BacktestEngine(settings, client)
            result = await engine.run("BTCUSDT", "4h", limit=10)

        # df tem 10 candles e warmup=10 → candles_used=0, nenhum sinal avaliado
        assert result.candles_used == 0
        assert result.total_trades == 0
        assert not evaluate_called


class TestBacktestEngineMaxDrawdown:
    """TEST_011_05 — max_drawdown calculado corretamente (pior pico→vale)."""

    def test_calc_metrics_drawdown(self) -> None:
        from src.backtest.models import BacktestTrade

        def _trade(pnl: float) -> BacktestTrade:
            return BacktestTrade(
                symbol="BTCUSDT",
                timeframe="4h",
                direction="LONG",
                entry_price=100.0,
                sl_price=95.0,
                tp_price=110.0,
                entry_candle_idx=0,
                exit_candle_idx=1,
                exit_price=110.0 if pnl > 0 else 95.0,
                close_reason="TP" if pnl > 0 else "SL",
                pnl_usdt=pnl,
                rrr_realizado=2.0 if pnl > 0 else 0.5,
            )

        # sequência: +10, +10, -30, +5
        # equity acumulada: 10, 20, -10, -5
        # pico = 20, vale mínimo = -10 → drawdown = -10 - 20 = -30
        settings = _make_settings()
        client = AsyncMock()
        engine = BacktestEngine(settings, client)

        trades = [_trade(10), _trade(10), _trade(-30), _trade(5)]
        metrics = engine._calc_metrics(trades)

        assert metrics["max_drawdown_usdt"] == pytest.approx(-30.0, abs=0.01)
        assert metrics["total_trades"] == 4
        assert metrics["win_rate_pct"] == pytest.approx(75.0, abs=0.01)


class TestBacktestEnginePaginacao:
    """Regressão: _fetch_ohlcv deve paginar com since crescente, não repetir velas."""

    @pytest.mark.asyncio
    async def test_since_cresce_entre_batches(self) -> None:
        """limit=1500 força 2 calls (1000 + 500); since do 2º > since do 1º."""
        candle_ms = 900_000  # 15m
        sinces_received: list[int | None] = []

        async def _mock(sym, tf, limit=200, since=None):
            # Mock retorna timestamps iniciando a partir do since recebido
            assert since is not None
            sinces_received.append(since)
            times = [pd.Timestamp((since + i * candle_ms) * 1_000_000) for i in range(limit)]
            return pd.DataFrame(
                {
                    "open_time": times,
                    "open": [100.0] * limit,
                    "high": [101.0] * limit,
                    "low": [99.0] * limit,
                    "close": [100.5] * limit,
                    "volume": [1000.0] * limit,
                }
            )

        settings = _make_settings(warmup=5)
        client = MagicMock()
        client.fetch_ohlcv = _mock

        engine = BacktestEngine(settings, client)
        result = await engine._fetch_ohlcv("ATOMUSDT", "15m", limit=1500)

        assert len(result) == 1500
        assert len(sinces_received) == 2  # 1000 + 500
        # since do segundo batch deve ser maior que o do primeiro
        assert sinces_received[1] > sinces_received[0]  # type: ignore[operator]

    @pytest.mark.asyncio
    async def test_sem_duplicatas_entre_batches(self) -> None:
        """drop_duplicates remove sobreposição de open_time entre batches."""
        candle_ms = 900_000
        calls = 0

        async def _mock_overlap(sym, tf, limit=200, since=None):
            nonlocal calls
            calls += 1
            assert since is not None
            # Batch 2 começa 1 candle antes do fim do batch 1 — cria sobreposição
            times = [pd.Timestamp((since + i * candle_ms) * 1_000_000) for i in range(limit)]
            return pd.DataFrame(
                {
                    "open_time": times,
                    "open": [100.0] * limit,
                    "high": [101.0] * limit,
                    "low": [99.0] * limit,
                    "close": [100.5] * limit,
                    "volume": [1000.0] * limit,
                }
            )

        settings = _make_settings(warmup=2)
        client = MagicMock()
        client.fetch_ohlcv = _mock_overlap

        engine = BacktestEngine(settings, client)
        result = await engine._fetch_ohlcv("ATOMUSDT", "15m", limit=1500)

        assert result["open_time"].is_unique
