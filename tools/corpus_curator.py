"""
Curador de corpus para validacao da SPEC_013 — SignalEngine Validation Suite.

Modos de uso:

    # Gera corpus v1 completo automaticamente (recomendado)
    python tools/corpus_curator.py --generate-v1 \\
        --symbol BTCUSDT,ETHUSDT --timeframe 15m,1h

    # Modo manual — candidatos com expected_signal=null para revisao
    python tools/corpus_curator.py --fetch-public \\
        --symbol BTCUSDT --timeframe 15m

    # Modo CSV
    python tools/corpus_curator.py --csv data/BTCUSDT_5m.csv \\
        --symbol BTCUSDT --timeframe 5m
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.monitoring.logger import configure_logging, get_logger  # noqa: E402
from src.strategy.indicators import (  # noqa: E402
    compute_all,
    last_valid_fractal_high,
    last_valid_fractal_low,
)
from src.strategy.signal_engine import Direction, SignalEngine  # noqa: E402

configure_logging("INFO")
logger = get_logger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────────

DEFAULT_OUTPUT = "docs/corpus/signal_corpus_draft.json"
DEFAULT_OUTPUT_V1 = "docs/corpus/signal_corpus_v1.json"
MIN_CANDLES = 50
SNAPSHOT_SIZE = 210  # candles armazenados por caso para replay nos testes

_ENGINE = SignalEngine(risk_reward_ratio=2.0)


# ─── Leitura de dados ─────────────────────────────────────────────────────────


def load_csv(path: str) -> pd.DataFrame:
    """Le um CSV com colunas OHLCV e retorna DataFrame padronizado."""
    logger.info("carregando_csv", path=path)
    df = pd.read_csv(path)
    df.columns = [c.lower().strip() for c in df.columns]

    required = {"open_time", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV sem colunas obrigatorias: {sorted(missing)}")

    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
    df = df.sort_values("open_time").reset_index(drop=True)
    logger.info("csv_carregado", total_candles=len(df))
    return df


async def fetch_from_binance(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    """Busca candles OHLCV da Binance usando credenciais do .env."""
    from src.config.settings import get_settings
    from src.exchange.binance_client import BinanceClient

    settings = get_settings()
    client = BinanceClient(settings)
    try:
        await client.connect()
        df = await client.fetch_ohlcv_with_retry(symbol, timeframe, limit=limit)
        logger.info("ohlcv_obtido", total_candles=len(df))
        return df
    finally:
        await client.close()


def fetch_public(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    """Busca candles via API publica da Binance Futures (sem autenticacao)."""
    import urllib.request

    url = (
        f"https://fapi.binance.com/fapi/v1/klines"
        f"?symbol={symbol.upper()}&interval={timeframe}&limit={limit}"
    )
    logger.info("buscando_ohlcv_publico", symbol=symbol, timeframe=timeframe, limit=limit)

    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
        raw = json.loads(resp.read().decode())

    rows = [
        {
            "open_time": pd.Timestamp(r[0], unit="ms", tz="UTC"),
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "volume": float(r[5]),
        }
        for r in raw
    ]
    df = pd.DataFrame(rows)
    logger.info("ohlcv_publico_obtido", total_candles=len(df))
    return df


# ─── Auto-anotacao via SignalEngine ───────────────────────────────────────────


def _auto_annotate(df_raw: pd.DataFrame, symbol: str, timeframe: str) -> str | None:
    """Executa SignalEngine no DataFrame e retorna 'long', 'short' ou None.

    Usa o DataFrame raw (sem indicadores pre-computados) para que o engine
    processe exatamente como faria em producao.
    """
    signal = _ENGINE.evaluate(symbol, timeframe, df_raw)
    if signal is None:
        return None
    return "long" if signal.direction == Direction.LONG else "short"


def _ohlcv_snapshot(df_raw: pd.DataFrame, up_to_idx: int) -> list[list]:
    """Retorna os ultimos SNAPSHOT_SIZE candles ate up_to_idx como lista compacta.

    Formato: [[open_time_ms, open, high, low, close, volume], ...]
    Usado pelo test suite para replay sem dependencia da Binance.
    """
    start = max(0, up_to_idx - SNAPSHOT_SIZE + 1)
    slice_df = df_raw.iloc[start : up_to_idx + 1]
    rows = []
    for _, row in slice_df.iterrows():
        ts = row["open_time"]
        ts_ms = int(ts.value // 1_000_000) if hasattr(ts, "value") else int(ts.timestamp() * 1000)
        rows.append(
            [
                ts_ms,
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                float(row["volume"]),
            ]
        )
    return rows


# ─── Avaliacao de condicoes por barra ─────────────────────────────────────────


def _alligator_description(jaw: float, teeth: float, lips: float, close: float) -> str:
    if lips > teeth > jaw and close > lips:
        return "alligator bullish — lips > teeth > jaw, preco acima"
    if lips < teeth < jaw and close < lips:
        return "alligator bearish — lips < teeth < jaw, preco abaixo"
    if lips > teeth > jaw:
        return "alligator bullish (estrutura ok, preco abaixo das linhas)"
    if lips < teeth < jaw:
        return "alligator bearish (estrutura ok, preco acima das linhas)"
    return "alligator em consolidacao"


def _lips_direction(lips_series: pd.Series, idx: int) -> str:
    if idx < 1:
        return "indefinida"
    prev = lips_series.iloc[idx - 1]
    curr = lips_series.iloc[idx]
    if pd.isna(prev) or pd.isna(curr):
        return "indefinida"
    if curr > prev:
        return "up"
    if curr < prev:
        return "down"
    return "flat"


def _find_fractal_bar_index(
    df_enriched: pd.DataFrame,
    fractal_price: float,
    column: str,
    current_idx: int,
) -> int | None:
    lookback_start = max(0, current_idx - 102)
    search_slice = df_enriched[column].iloc[lookback_start : current_idx - 1]
    matches = search_slice[search_slice == fractal_price]
    if matches.empty:
        return None
    fractal_pos = int(matches.index[-1])
    return fractal_pos - current_idx


def _evaluate_bar(
    df_enriched: pd.DataFrame,
    df_raw: pd.DataFrame,
    idx: int,
    min_conditions: int,
    auto_annotate: bool,
    symbol: str,
    timeframe: str,
) -> dict[str, Any] | None:
    """Avalia barra `idx` para candidatura. Sem look-ahead bias."""
    row = df_enriched.iloc[idx]

    jaw = row.get("jaw")
    teeth = row.get("teeth")
    lips = row.get("lips")
    ao = row.get("ao")
    ao_prev = df_enriched["ao"].iloc[idx - 1] if idx >= 1 else None

    if any(pd.isna(v) for v in [jaw, teeth, lips, ao]):
        return None

    jaw_f, teeth_f, lips_f, ao_f = float(jaw), float(teeth), float(lips), float(ao)
    close = float(row["close"])

    df_slice = df_enriched.iloc[: idx + 1]
    fractal_high = last_valid_fractal_high(df_slice)
    fractal_low = last_valid_fractal_low(df_slice)

    alligator_bullish = lips_f > teeth_f > jaw_f and close > lips_f
    ao_positive = ao_f > 0
    close_above_fractal_high = fractal_high is not None and close > fractal_high
    valid_sl_fractal_low = fractal_low is not None and fractal_low < close

    long_conditions = sum(
        [alligator_bullish, ao_positive, close_above_fractal_high, valid_sl_fractal_low]
    )

    alligator_bearish = lips_f < teeth_f < jaw_f and close < lips_f
    ao_negative = ao_f < 0
    close_below_fractal_low = fractal_low is not None and close < fractal_low
    valid_sl_fractal_high = fractal_high is not None and fractal_high > close

    short_conditions = sum(
        [alligator_bearish, ao_negative, close_below_fractal_low, valid_sl_fractal_high]
    )

    total_conditions = max(long_conditions, short_conditions)
    if total_conditions < min_conditions:
        return None

    if long_conditions > short_conditions:
        direction = "long"
    elif short_conditions > long_conditions:
        direction = "short"
    else:
        direction = "ambiguous"

    if direction in ("long", "ambiguous") and fractal_high is not None:
        fractal_ref_price, fractal_ref_type, fractal_ref_col = fractal_high, "high", "fractal_high"
    elif direction == "short" and fractal_low is not None:
        fractal_ref_price, fractal_ref_type, fractal_ref_col = fractal_low, "low", "fractal_low"
    else:
        fractal_ref_price, fractal_ref_type, fractal_ref_col = fractal_high, "high", "fractal_high"

    fractal_bar_index: int | None = None
    if fractal_ref_price is not None:
        fractal_bar_index = _find_fractal_bar_index(
            df_enriched, fractal_ref_price, fractal_ref_col, idx
        )

    crossing_zero = False
    if ao_prev is not None and not pd.isna(ao_prev):
        ao_prev_f = float(ao_prev)
        crossing_zero = (ao_prev_f <= 0 < ao_f) or (ao_prev_f >= 0 > ao_f)

    ts = row["open_time"]
    date_str = ts.isoformat().replace("+00:00", "Z") if hasattr(ts, "isoformat") else str(ts)

    # Auto-anotacao: usa SignalEngine no slice raw sem look-ahead
    if auto_annotate:
        df_raw_slice = df_raw.iloc[: idx + 1].copy()
        expected_signal = _auto_annotate(df_raw_slice, symbol, timeframe)
    else:
        expected_signal = None

    snapshot = _ohlcv_snapshot(df_raw, idx) if auto_annotate else None

    result: dict[str, Any] = {
        "date": date_str,
        "direction": direction,
        "fractal_ref": {
            "type": fractal_ref_type,
            "price": round(fractal_ref_price, 8) if fractal_ref_price is not None else None,
            "bar_index": fractal_bar_index,
        },
        "alligator_state": {
            "jaw": round(jaw_f, 8),
            "teeth": round(teeth_f, 8),
            "lips": round(lips_f, 8),
            "jaw_above_teeth": jaw_f > teeth_f,
            "teeth_above_lips": teeth_f > lips_f,
            "lips_direction": _lips_direction(df_enriched["lips"], idx),
            "description": _alligator_description(jaw_f, teeth_f, lips_f, close),
        },
        "ao_value": {
            "current": round(ao_f, 8),
            "prev": round(float(ao_prev), 8)
            if ao_prev is not None and not pd.isna(ao_prev)
            else None,
            "crossing_zero": crossing_zero,
            "histogram_color": "green" if ao_f >= 0 else "red",
        },
        "close": round(close, 8),
        "conditions_met": {
            "alligator_bullish": alligator_bullish,
            "ao_positive": ao_positive,
            "close_above_fractal_high": close_above_fractal_high,
            "valid_sl_fractal_low": valid_sl_fractal_low,
        },
        "expected_signal": expected_signal,
        "notes": "auto-gerado pelo SignalEngine" if auto_annotate else "",
    }

    if snapshot is not None:
        result["ohlcv_snapshot"] = snapshot

    return result


# ─── Pipeline principal ───────────────────────────────────────────────────────


def curate(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    min_conditions: int,
    max_cases: int | None,
    auto_annotate: bool = False,
) -> list[dict[str, Any]]:
    """Processa DataFrame e retorna lista de casos candidatos."""
    if len(df) < MIN_CANDLES:
        raise ValueError(f"DataFrame com {len(df)} candles; minimo: {MIN_CANDLES}")

    logger.info("calculando_indicadores", symbol=symbol, timeframe=timeframe, total_candles=len(df))
    df_enriched = compute_all(df)
    last_valid_idx = len(df_enriched) - 2  # descarta ultimo candle (aberto)

    logger.info("avaliando_barras", barras_avaliadas=last_valid_idx, min_conditions=min_conditions)

    cases: list[dict[str, Any]] = []
    for i in range(MIN_CANDLES, last_valid_idx + 1):
        result = _evaluate_bar(df_enriched, df, i, min_conditions, auto_annotate, symbol, timeframe)
        if result is not None:
            cases.append(result)

    logger.info("candidatos_encontrados", total=len(cases))

    if max_cases is not None and len(cases) > max_cases:
        cases = cases[-max_cases:]
        logger.info("casos_apos_limite", total=len(cases), max_cases=max_cases)

    corpus: list[dict[str, Any]] = []
    for seq, case in enumerate(cases, start=1):
        entry: dict[str, Any] = {
            "case_id": f"CASE_{seq:03d}",
            "symbol": symbol,
            "timeframe": timeframe,
        }
        entry.update(case)
        corpus.append(entry)

    return corpus


# ─── Modo generate-v1: corpus balanceado automatico ──────────────────────────


def _collect_by_signal(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Retorna (longs, shorts, nones) com auto-anotacao completa."""
    all_cases = curate(df, symbol, timeframe, min_conditions=0, max_cases=None, auto_annotate=True)
    longs = [c for c in all_cases if c["expected_signal"] == "long"]
    shorts = [c for c in all_cases if c["expected_signal"] == "short"]
    nones = [c for c in all_cases if c["expected_signal"] is None]
    logger.info(
        "casos_coletados",
        symbol=symbol,
        timeframe=timeframe,
        longs=len(longs),
        shorts=len(shorts),
        nones=len(nones),
    )
    return longs, shorts, nones


def generate_v1(
    symbols: list[str],
    timeframes: list[str],
    output_path: Path,
    use_public: bool = True,
    limit: int = 1000,
    target_long: int = 8,
    target_short: int = 8,
    target_none: int = 4,
) -> None:
    """Gera signal_corpus_v1.json com corpus balanceado auto-anotado."""
    all_longs: list[dict] = []
    all_shorts: list[dict] = []
    all_nones: list[dict] = []

    for symbol in symbols:
        for timeframe in timeframes:
            try:
                df = fetch_public(symbol, timeframe, limit)
            except Exception as exc:
                logger.warning(
                    "fetch_falhou",
                    symbol=symbol,
                    timeframe=timeframe,
                    error_type=type(exc).__name__,
                )
                continue
            longs, shorts, nones = _collect_by_signal(df, symbol, timeframe)
            all_longs.extend(longs)
            all_shorts.extend(shorts)
            all_nones.extend(nones)

    # Seleciona os casos mais recentes de cada categoria
    selected_longs = all_longs[-target_long:] if len(all_longs) >= target_long else all_longs
    selected_shorts = all_shorts[-target_short:] if len(all_shorts) >= target_short else all_shorts
    selected_nones = all_nones[-target_none:] if len(all_nones) >= target_none else all_nones

    logger.info(
        "selecao_final",
        longs=len(selected_longs),
        shorts=len(selected_shorts),
        nones=len(selected_nones),
    )

    if len(selected_longs) < target_long:
        logger.warning("longs_insuficientes", encontrado=len(selected_longs), esperado=target_long)
    if len(selected_shorts) < target_short:
        logger.warning(
            "shorts_insuficientes", encontrado=len(selected_shorts), esperado=target_short
        )
    if len(selected_nones) < target_none:
        logger.warning("nones_insuficientes", encontrado=len(selected_nones), esperado=target_none)

    corpus = selected_longs + selected_shorts + selected_nones

    # Renumera case_ids
    for i, case in enumerate(corpus, 1):
        case["case_id"] = f"CASE_{i:03d}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(corpus, fh, indent=2, ensure_ascii=False, cls=_SafeEncoder)

    total = len(corpus)
    print(
        f"\n=== Corpus v1 gerado: {output_path} ===\n"
        f"Total casos : {total}\n"
        f"Long        : {len(selected_longs)}\n"
        f"Short       : {len(selected_shorts)}\n"
        f"Sem sinal   : {len(selected_nones)}\n"
        f"\nCorpus pronto para: pytest tests/strategy/test_signal_engine_corpus.py -v\n"
    )


# ─── Serializacao JSON ────────────────────────────────────────────────────────


class _SafeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if hasattr(o, "item") and hasattr(o, "dtype"):
            return o.item()
        if isinstance(o, float) and o != o:
            return None
        if hasattr(o, "isoformat"):
            return o.isoformat()
        return super().default(o)


# ─── CLI ──────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="corpus_curator",
        description=(
            "Gera corpus para validacao da SPEC_013. "
            "Use --generate-v1 para corpus completo automatico."
        ),
    )

    parser.add_argument(
        "--generate-v1",
        action="store_true",
        dest="generate_v1",
        help=(
            "Gera signal_corpus_v1.json completo e auto-anotado. "
            "Requer --symbol e --timeframe (virgula-separados)."
        ),
    )

    source = parser.add_mutually_exclusive_group()
    source.add_argument("--csv", metavar="ARQUIVO", help="CSV com colunas OHLCV")
    source.add_argument("--fetch", action="store_true", help="Binance com credenciais do .env")
    source.add_argument(
        "--fetch-public",
        action="store_true",
        dest="fetch_public",
        help="API publica da Binance Futures (sem credenciais)",
    )

    parser.add_argument(
        "--symbol", required=True, help="Simbolo(s), ex: BTCUSDT ou BTCUSDT,ETHUSDT"
    )
    parser.add_argument("--timeframe", required=True, help="Timeframe(s), ex: 15m ou 15m,1h")
    parser.add_argument("--limit", type=int, default=1000, help="Candles a buscar (default: 1000)")
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Arquivo JSON de saida (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--min-conditions",
        type=int,
        default=2,
        dest="min_conditions",
        help="Min condicoes para candidatura (default: 2)",
    )
    parser.add_argument(
        "--max-cases", type=int, default=None, dest="max_cases", help="Limite de casos na saida"
    )
    parser.add_argument(
        "--auto-annotate",
        action="store_true",
        dest="auto_annotate",
        help="Auto-anota expected_signal via SignalEngine e inclui ohlcv_snapshot",
    )

    return parser


async def _async_main(args: argparse.Namespace) -> None:
    # ─── Modo generate-v1 ─────────────────────────────────────────────────────
    if args.generate_v1:
        symbols = [s.strip().upper() for s in args.symbol.split(",") if s.strip()]
        timeframes = [t.strip().lower() for t in args.timeframe.split(",") if t.strip()]
        output = Path(args.output if args.output != DEFAULT_OUTPUT else DEFAULT_OUTPUT_V1)
        generate_v1(symbols, timeframes, output, use_public=True, limit=args.limit)
        return

    # ─── Modo single symbol/timeframe ─────────────────────────────────────────
    if not (args.csv or args.fetch or args.fetch_public):
        print("Erro: fora do modo --generate-v1, informe --csv, --fetch ou --fetch-public.")
        sys.exit(1)

    symbol = args.symbol.upper()
    timeframe = args.timeframe.lower()

    if args.fetch:
        df = await fetch_from_binance(symbol, timeframe, args.limit)
    elif args.fetch_public:
        df = fetch_public(symbol, timeframe, args.limit)
    else:
        df = load_csv(args.csv)

    corpus = curate(
        df=df,
        symbol=symbol,
        timeframe=timeframe,
        min_conditions=args.min_conditions,
        max_cases=args.max_cases,
        auto_annotate=args.auto_annotate,
    )

    if not corpus:
        print(f"Nenhum caso encontrado com min_conditions={args.min_conditions}.")
        return

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(corpus, fh, indent=2, ensure_ascii=False, cls=_SafeEncoder)

    logger.info("corpus_salvo", path=str(output_path), total_casos=len(corpus))
    print(f"\nCorpus gerado: {output_path} — {len(corpus)} casos.\n")


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    parser = _build_parser()
    args = parser.parse_args()

    asyncio.run(_async_main(args))


if __name__ == "__main__":
    _root = str(Path(__file__).resolve().parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)
    main()
