from __future__ import annotations

import asyncio
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pandas as pd

from src.backtest.models import BacktestResult, BacktestTrade
from src.config.settings import Settings
from src.exchange.binance_client import BinanceClient
from src.strategy.signal_engine import Direction, Signal, SignalEngine
from src.trading.risk_manager import RiskManager

# Duração de cada timeframe em milissegundos — usado para paginação por since
_TF_MS: dict[str, int] = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "6h": 21_600_000,
    "8h": 28_800_000,
    "12h": 43_200_000,
    "1d": 86_400_000,
}


class BacktestEngine:
    def __init__(
        self,
        settings: Settings,
        client: BinanceClient,
        risk_manager: RiskManager | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._risk_manager = risk_manager
        self._signal_engine = SignalEngine(risk_reward_ratio=settings.risk_reward_ratio)
        self._last_log_ts: float = 0.0

    def _apply_costs(
        self,
        price: float,
        direction: Literal["LONG", "SHORT"],
        symbol: str,
        order_type: Literal["market", "stop"],
        slippage_override: float | None = None,
        is_exit: bool = False,
    ) -> tuple[float, float, float]:
        """Aplica slippage percentual por tier e taxa no preço dado.

        O slippage é sempre adverso: na entrada (comprar) o preço sobe;
        na saída (vender) o preço desce.

        Args:
            price: Preço de referência (close do candle ou SL/TP).
            direction: Direção do trade.
            symbol: Símbolo para lookup do tier de liquidez.
            order_type: 'market' (entrada) ou 'stop' (SL/TP).
            slippage_override: Se fornecido, sobrescreve slippage do tier.
            is_exit: Se True, inverte direção do slippage (saída é oposta).

        Returns:
            (price_with_slippage, fee_amount, slippage_amount_usdt)
        """
        if slippage_override is not None:
            slippage_pct = max(0.0, slippage_override)
        else:
            liq_tier = self._settings.backtest_slippage_liq_map.get(symbol, "medium")
            slippage_pct = self._settings.backtest_slippage_by_liq.get(liq_tier, 0.0008)

        fee_pct = (
            self._settings.backtest_maker_fee
            if order_type == "stop"
            else self._settings.backtest_taker_fee
        )

        # Slippage adverso: na saída inverte direção
        slip_dir = direction
        if is_exit:
            slip_dir = "SHORT" if direction == "LONG" else "LONG"

        if slip_dir == "LONG":
            adjusted_price = price * (1 + slippage_pct)
        else:
            adjusted_price = price * (1 - slippage_pct)

        fee = adjusted_price * fee_pct
        slippage_amount = abs(adjusted_price - price)
        return adjusted_price, fee, slippage_amount

    # ── SPEC_028: Alertas informacionais ──────────────────────────────

    def _build_warnings(
        self,
        trades: list[BacktestTrade],
        gross_result: BacktestResult,
        net_result: BacktestResult,
        symbol: str,
    ) -> list[str]:
        """Gera alertas informacionais sobre confiabilidade do resultado.

        Quatro condições (SPEC_028 §5.4):
        1. N < 50 → IC 95% Wilson para win rate
        2. net/gross < 0.5 → degradação alta
        3. Combinado (ambas acima)
        4. >3 runs no mesmo par em 24h → data dredging
        """
        warnings: list[str] = []
        n = len(trades)

        # ── Condição 1: baixa significância (N < 50) ──
        if 0 < n < 50:
            wins = sum(1 for t in trades if t.pnl_gross_usdt > 0)
            p_hat = wins / n
            z = 1.96  # 95% confidence
            denom = 1 + z**2 / n
            center = (p_hat + z**2 / (2 * n)) / denom
            margin = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n) / denom
            ci_low = max(0.0, center - margin) * 100
            ci_high = min(1.0, center + margin) * 100
            warnings.append(
                f"IC 95% win rate: [{ci_low:.1f}%, {ci_high:.1f}%] — "
                f"N={n} < 50, baixa significância estatística"
            )

        # ── Condição 2: degradação por custos (net/gross < 0.5) ──
        gross_pnl = gross_result.total_pnl_usdt
        net_pnl = net_result.total_pnl_usdt
        if gross_pnl > 0:
            ratio = net_pnl / gross_pnl
            if ratio < 0.5:
                degradation = (1 - ratio) * 100
                warnings.append(
                    "Degradação alta: custos consomem >50% do lucro bruto "
                    f"(razão net/gross={ratio:.2f}, {degradation:.1f}% consumido)"
                )
            else:
                degradation = (1 - ratio) * 100
                warnings.append(
                    f"Razão net/gross: {ratio:.2f} — "
                    f"custos consumiram {degradation:.1f}% do lucro bruto"
                )

        # ── Condição 3: combinado (N < 50 + degradação alta) ──
        if 0 < n < 50 and gross_pnl > 0 and (net_pnl / gross_pnl) < 0.5:
            warnings.append(
                "Baixa significância + degradação alta — "
                "resultado não confiável para tomada de decisão"
            )

        # ── Condição 4: múltiplas execuções (data dredging) ──
        try:
            run_log = Path("backtest_runs.jsonl")
            if run_log.exists():
                count = 0
                now = datetime.now(UTC)
                for line in run_log.read_text(encoding="utf-8").splitlines():
                    try:
                        entry = json.loads(line)
                        if entry.get("symbol") == symbol:
                            ts_str = entry.get("ts", "")
                            if ts_str:
                                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                if (now - ts).total_seconds() < 86400:
                                    count += 1
                    except (json.JSONDecodeError, ValueError):
                        continue
                if count >= 3:
                    warnings.append(
                        f"Múltiplas execuções detectadas ({count} nas últimas 24h) "
                        "— risco de data dredging. "
                        "Considere walk-forward validation."
                    )
        except OSError:
            pass  # Falha silenciosa — logging é best-effort

        return warnings

    # ── SPEC_028: Processamento de trade fechado ─────────────────────

    def _process_closed_trade(
        self,
        symbol: str,
        direction: Literal["LONG", "SHORT"],
        entry: float,
        sl: float,
        tp: float,
        exit_price: float,
        close_reason: Literal["SL", "TP"],
        entry_idx: int,
        exit_idx: int,
        initial_balance: float,
        realistic: bool,
        slippage_override: float | None = None,
    ) -> BacktestTrade:
        """Calcula custos, PnL e métricas de um trade fechado.

        No modo realista aplica slippage, taxas e position sizing via RiskManager.
        No modo legado preserva a fórmula linear original (SPEC_011).
        """
        if realistic:
            entry_adj, entry_fee_pu, entry_slip_pu = self._apply_costs(
                entry, direction, symbol, "market", slippage_override=slippage_override
            )
            exit_adj, exit_fee_pu, exit_slip_pu = self._apply_costs(
                exit_price,
                direction,
                symbol,
                "stop" if close_reason in ("SL", "TP") else "market",
                slippage_override=slippage_override,
                is_exit=True,
            )

            # Position sizing via RiskManager
            dir_enum = Direction.LONG if direction == "LONG" else Direction.SHORT
            if self._risk_manager is not None:
                trade_signal = Signal(
                    symbol=symbol,
                    timeframe="",  # timeframe is not used in this context
                    direction=dir_enum,
                    entry_price=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    fractal_ref=entry,
                )
                position_result = self._risk_manager.calculate(
                    signal=trade_signal,
                    available_balance=initial_balance,
                )
                qty = (
                    position_result.unwrap().quantity
                    if position_result.is_ok()
                    else (initial_balance / entry_adj)
                )
            else:
                qty = initial_balance / entry_adj

            # Gross PnL (fórmula original, preço de referência)
            if direction == "LONG":
                pnl_gross = (exit_price - entry) * initial_balance / entry
                pnl_net_price = (exit_adj - entry_adj) * qty
            else:
                pnl_gross = (entry - exit_price) * initial_balance / entry
                pnl_net_price = (entry_adj - exit_adj) * qty

            # Custos em USDT
            entry_fee_usdt = entry_fee_pu * qty
            exit_fee_usdt = exit_fee_pu * qty
            entry_slip_usdt = entry_slip_pu * qty
            exit_slip_usdt = exit_slip_pu * qty
            pnl_net = pnl_net_price - entry_fee_usdt - exit_fee_usdt
        else:
            entry_adj = entry
            exit_adj = exit_price
            entry_fee_usdt = exit_fee_usdt = 0.0
            entry_slip_usdt = exit_slip_usdt = 0.0
            entry_fee_pu = exit_fee_pu = 0.0
            entry_slip_pu = exit_slip_pu = 0.0

            if direction == "LONG":
                pnl_gross = (exit_price - entry) * initial_balance / entry
                pnl_net = pnl_gross
            else:
                pnl_gross = (entry - exit_price) * initial_balance / entry
                pnl_net = pnl_gross

        risk_dist = abs(entry - sl)
        reward_dist = abs(exit_price - entry)
        rrr = reward_dist / risk_dist if risk_dist > 0 else 0.0

        slippage_entry_pct = abs(entry_adj - entry) / entry * 100 if entry else 0
        slippage_exit_pct = abs(exit_adj - exit_price) / exit_price * 100 if exit_price else 0

        return BacktestTrade(
            symbol=symbol,
            timeframe="",  # timeframe set by caller via trades list context
            direction=direction,
            entry_price=entry_adj,
            sl_price=sl,
            tp_price=tp,
            entry_candle_idx=entry_idx,
            exit_candle_idx=exit_idx,
            exit_price=exit_adj,
            close_reason=close_reason,
            pnl_usdt=round(pnl_gross, 4),
            rrr_realizado=round(rrr, 4),
            entry_fee=round(entry_fee_usdt, 4),
            exit_fee=round(exit_fee_usdt, 4),
            slippage_entry_pct=round(slippage_entry_pct, 4),
            slippage_exit_pct=round(slippage_exit_pct, 4),
            slippage_entry_usdt=round(entry_slip_usdt, 4),
            slippage_exit_usdt=round(exit_slip_usdt, 4),
            pnl_gross_usdt=round(pnl_gross, 4),
            pnl_net_usdt=round(pnl_net, 4),
        )

    # ── SPEC_028: Logging de parâmetros (JSONL) ──────────────────────

    def _log_backtest_run(
        self,
        symbol: str,
        timeframe: str,
        realistic: bool,
        gross_pnl: float,
        net_pnl: float,
        n_trades: int,
        warnings: list[str],
        slippage_override: float | None = None,
    ) -> None:
        """Append em backtest_runs.jsonl com parâmetros + resultado.

        Falha de escrita nunca interrompe o backtest.
        Rate-limit: 1 linha por segundo no mesmo engine.
        """
        now = time.time()
        if now - self._last_log_ts < 1.0:
            return  # rate-limit
        self._last_log_ts = now

        try:
            log_entry = {
                "ts": datetime.now(UTC).isoformat(),
                "symbol": symbol,
                "tf": timeframe,
                "params": {
                    "realistic": realistic,
                    "slippage_override": slippage_override,
                },
                "gross_pnl": round(gross_pnl, 4),
                "net_pnl": round(net_pnl, 4),
                "n_trades": n_trades,
                "warnings": warnings,
            }
            log_path = Path("backtest_runs.jsonl")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except OSError:
            pass  # Falha silenciosa — nunca interrompe backtest

    async def _fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        candle_ms = _TF_MS.get(timeframe, 60_000)
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        since = now_ms - limit * candle_ms

        frames: list[pd.DataFrame] = []
        while True:
            fetched = sum(len(f) for f in frames)
            remaining = limit - fetched
            if remaining <= 0:
                break
            batch = min(1000, remaining)
            df = await self._client.fetch_ohlcv(symbol, timeframe, limit=batch, since=since)
            if df.empty:
                break
            frames.append(df)
            # Avança since para depois da última vela recebida — evita re-buscar as mesmas velas
            last_ts_ms = pd.Timestamp(df["open_time"].iloc[-1]).value // 1_000_000
            since = last_ts_ms + candle_ms
            if len(df) < batch:
                break

        if not frames:
            return pd.DataFrame()
        result = pd.concat(frames, ignore_index=True)
        result = result.drop_duplicates(subset=["open_time"]).reset_index(drop=True)
        return result

    def _calc_metrics(self, trades: list[BacktestTrade]) -> dict[str, float]:
        if not trades:
            return {
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "total_pnl_usdt": 0.0,
                "avg_rrr": 0.0,
                "max_drawdown_usdt": 0.0,
                "profit_factor": 0.0,
            }

        wins = [t for t in trades if t.pnl_usdt > 0]
        losses = [t for t in trades if t.pnl_usdt <= 0]
        win_rate = len(wins) / len(trades) * 100.0
        total_pnl = sum(t.pnl_usdt for t in trades)
        avg_rrr = sum(t.rrr_realizado for t in trades) / len(trades)

        gross_profit = sum(t.pnl_usdt for t in wins)
        gross_loss = abs(sum(t.pnl_usdt for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else math.inf

        # pico→vale sobre equity acumulada
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for t in trades:
            equity += t.pnl_usdt
            if equity > peak:
                peak = equity
            drawdown = equity - peak
            if drawdown < max_drawdown:
                max_drawdown = drawdown

        return {
            "total_trades": len(trades),
            "win_rate_pct": round(win_rate, 2),
            "total_pnl_usdt": round(total_pnl, 4),
            "avg_rrr": round(avg_rrr, 4),
            "max_drawdown_usdt": round(max_drawdown, 4),
            "profit_factor": round(profit_factor, 4) if not math.isinf(profit_factor) else 0.0,
        }

    def _build_result(
        self,
        symbol: str,
        timeframe: str,
        trades: list[BacktestTrade],
        candles_used: int,
        pnl_field: str = "pnl_usdt",
    ) -> BacktestResult:
        """Constrói BacktestResult a partir de trades usando um campo de PnL específico.

        Args:
            pnl_field: Nome do campo de PnL a usar (pnl_usdt, pnl_gross_usdt, pnl_net_usdt).
        """
        if not trades:
            return BacktestResult(
                symbol=symbol,
                timeframe=timeframe,
                candles_used=candles_used,
                generated_at=datetime.utcnow(),
            )

        n_trades = len(trades)
        wins = [t for t in trades if getattr(t, pnl_field) > 0]
        losses = [t for t in trades if getattr(t, pnl_field) <= 0]
        win_rate = len(wins) / n_trades * 100.0
        total_pnl = sum(getattr(t, pnl_field) for t in trades)
        avg_rrr = sum(t.rrr_realizado for t in trades) / n_trades

        gross_profit = sum(getattr(t, pnl_field) for t in wins)
        gross_loss = abs(sum(getattr(t, pnl_field) for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else math.inf

        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for t in trades:
            equity += getattr(t, pnl_field)
            if equity > peak:
                peak = equity
            drawdown = equity - peak
            if drawdown < max_drawdown:
                max_drawdown = drawdown

        return BacktestResult(
            symbol=symbol,
            timeframe=timeframe,
            candles_used=candles_used,
            trades=trades,
            total_trades=n_trades,
            win_rate_pct=round(win_rate, 2),
            total_pnl_usdt=round(total_pnl, 4),
            avg_rrr=round(avg_rrr, 4),
            max_drawdown_usdt=round(max_drawdown, 4),
            profit_factor=round(profit_factor, 4) if not math.isinf(profit_factor) else 0.0,
            generated_at=datetime.utcnow(),
        )

    async def run(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 1000,
        initial_balance: float = 1000.0,
        realistic: bool = False,
        slippage_override: float | None = None,
    ) -> BacktestResult:
        """Executa backtest da estratégia.

        Args:
            realistic: Se True, aplica slippage, taxas e prepara gross/net.
            slippage_override: Sobrescreve slippage do tier (gera WARN externamente).
        """
        df = await self._fetch_ohlcv(symbol, timeframe, limit)
        warmup = self._settings.warmup_candles

        if df.empty or len(df) <= warmup:
            return BacktestResult(
                symbol=symbol,
                timeframe=timeframe,
                candles_used=0,
                generated_at=datetime.utcnow(),
            )

        trades: list[BacktestTrade] = []
        open_trade: dict | None = None
        yield_every = 200

        for i in range(warmup, len(df)):
            if (i - warmup) % yield_every == 0:
                await asyncio.sleep(0)
            row = df.iloc[i]
            high = float(row["high"])
            low = float(row["low"])

            if open_trade is not None:
                direction = open_trade["direction"]
                tp = open_trade["tp"]
                sl = open_trade["sl"]
                entry = open_trade["entry"]
                close_reason: str | None = None
                exit_price: float | None = None

                if direction == "LONG":
                    if high >= tp:
                        close_reason = "TP"
                        exit_price = tp
                    elif low <= sl:
                        close_reason = "SL"
                        exit_price = sl
                else:
                    if low <= tp:
                        close_reason = "TP"
                        exit_price = tp
                    elif high >= sl:
                        close_reason = "SL"
                        exit_price = sl

                if close_reason is not None and exit_price is not None:
                    trade = self._process_closed_trade(
                        symbol=symbol,
                        direction=direction,
                        entry=entry,
                        sl=sl,
                        tp=tp,
                        exit_price=exit_price,
                        close_reason=close_reason,
                        entry_idx=open_trade["entry_idx"],
                        exit_idx=i,
                        initial_balance=initial_balance,
                        realistic=realistic,
                        slippage_override=slippage_override,
                    )
                    trades.append(trade)
                    open_trade = None

            if open_trade is None:
                window = df.iloc[: i + 1]
                signal = self._signal_engine.evaluate(symbol, timeframe, window)
                if signal is not None:
                    open_trade = {
                        "direction": signal.direction.value,
                        "entry": signal.entry_price,
                        "sl": signal.stop_loss,
                        "tp": signal.take_profit,
                        "entry_idx": i,
                    }

        candles_used = len(df) - warmup

        if realistic:
            gross_result = self._build_result(
                symbol, timeframe, trades, candles_used, "pnl_gross_usdt"
            )
            net_result = self._build_result(symbol, timeframe, trades, candles_used, "pnl_net_usdt")
            total_fees = sum(t.entry_fee + t.exit_fee for t in trades)
            total_slippage = sum(t.slippage_entry_usdt + t.slippage_exit_usdt for t in trades)

            net_result.gross = gross_result
            net_result.net = None  # self is the net result, avoid circular ref for serialization
            net_result.total_fees_usdt = round(total_fees, 4)
            net_result.total_slippage_usdt = round(total_slippage, 4)

            # ── Alertas informacionais + logging ──
            net_result.warnings = self._build_warnings(trades, gross_result, net_result, symbol)
            self._log_backtest_run(
                symbol=symbol,
                timeframe=timeframe,
                realistic=True,
                gross_pnl=gross_result.total_pnl_usdt,
                net_pnl=net_result.total_pnl_usdt,
                n_trades=len(trades),
                warnings=net_result.warnings,
                slippage_override=slippage_override,
            )
            return net_result
        else:
            result = self._build_result(symbol, timeframe, trades, candles_used, "pnl_usdt")
            result.gross = None  # no gross/net separation in simple mode
            result.net = None

            # ── Logging mesmo no modo simples ──
            self._log_backtest_run(
                symbol=symbol,
                timeframe=timeframe,
                realistic=False,
                gross_pnl=result.total_pnl_usdt,
                net_pnl=result.total_pnl_usdt,
                n_trades=len(trades),
                warnings=[],
                slippage_override=slippage_override,
            )
            return result
