"""
Módulo singleton de métricas Prometheus para o Phicube.

Uso:
    from src.monitoring.metrics import (
        trades_total,
        signals_total,
        heartbeat,
        get_metrics,
    )

    # Incrementar contador
    trades_total.labels(symbol="BTCUSDT", direction="long", status="open").inc()

    # Atualizar heartbeat
    heartbeat.set(time.time())

    # Obter texto formatado (para endpoint FastAPI)
    metrics_text = get_metrics()
"""

from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING

try:
    from importlib.metadata import version as _metadata_version
except ImportError:
    _metadata_version = None  # type: ignore[assignment]

from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)
from prometheus_client import start_http_server as prometheus_start_server

from src.monitoring.logger import get_logger

if TYPE_CHECKING:
    from typing import Literal

logger = get_logger(__name__)


def _get_version() -> str:
    """
    Retorna a versão do pacote a partir de pyproject.toml via importlib.metadata.

    Fallback para "0.1.0" se não for possível obter.
    """
    if _metadata_version is None:
        return "0.1.0"
    try:
        return _metadata_version("binance-phicube")
    except Exception:
        return "0.1.0"


# --- Info e Meta ---
phicube_info = Info(
    "phicube",
    "Informação estável da aplicação Phicube",
)

start_time = Gauge(
    "phicube_start_time_seconds",
    "Unix timestamp do startup da aplicação",
)

up = Gauge(
    "phicube_up",
    "Status da aplicação (1=saudável, 0=problema)",
)

heartbeat = Gauge(
    "phicube_heartbeat_seconds",
    "Unix timestamp do último heartbeat TradingMonitor",
)

positions_open = Gauge(
    "phicube_positions_open",
    "Quantidade de posições abertas atualmente",
)

pnl_usdt = Gauge(
    "phicube_pnl_usdt",
    "PnL acumulado em USDT (snapshot; pode ser negativo)",
    ["symbol"],  # label opcional
)

# --- Counters ---
signals_total = Counter(
    "phicube_signals_total",
    "Sinais válidos detectados pelo SignalEngine",
    ["symbol", "timeframe", "direction"],
)

signals_evaluated_total = Counter(
    "phicube_signals_evaluated_total",
    "Todas avaliações de sinal (base para rate de detecção)",
    ["symbol", "timeframe"],
)

signals_rejected_total = Counter(
    "phicube_signals_rejected_total",
    "Sinais rejeitados pelo RiskManager",
    ["symbol", "reason"],
)

trades_total = Counter(
    "phicube_trades_total",
    "Trades executados pelo OrderManager",
    ["symbol", "direction", "status"],
)

pnl_realized_win_total = Counter(
    "phicube_pnl_realized_win_total",
    "PnL positivo realizado (sempre crescente)",
    ["symbol"],
)

pnl_realized_loss_total = Counter(
    "phicube_pnl_realized_loss_total",
    "PnL negativo realizado (valor absoluto; sempre crescente)",
    ["symbol"],
)

errors_total = Counter(
    "phicube_errors_total",
    "Erros capturados por módulo",
    ["module", "error_type"],
)

api_requests_total = Counter(
    "phicube_api_requests_total",
    "Chamadas à API Binance",
    ["endpoint", "status"],
)

# --- Histograms ---
candle_latency_seconds = Histogram(
    "phicube_candle_latency_seconds",
    "Latência de fetch_ohlcv() em segundos",
    ["symbol"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

tick_duration_seconds = Histogram(
    "phicube_tick_duration_seconds",
    "Duração total de um _tick() completo",
    ["symbol", "timeframe"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# --- Runtime ---
monitor_count = Gauge(
    "phicube_monitor_count",
    "Número de TradingMonitors ativos",
)


def initialize(
    version: str | None = None,
    testnet: bool = True,
    python_version: str | None = None,
) -> None:
    """
    Inicializa métricas de info no startup.

    Deve ser chamado UMA VEZ no início do _main().
    """
    if version is None:
        version = _get_version()
    if python_version is None:
        vi = sys.version_info
        python_version = f"{vi.major}.{vi.minor}.{vi.micro}"

    phicube_info.info(
        {
            "version": version,
            "testnet": str(testnet).lower(),
            "python_version": python_version,
        }
    )
    start_time.set(time.time())
    up.set(1)
    logger.info("metrics_initialized", version=version, testnet=testnet)


def start_metrics_server(port: int, bind_host: str = "0.0.0.0") -> None:
    """
    Inicia o servidor HTTP embutido do prometheus_client.

    Executa em thread separada (built-in da lib).
    Não bloqueia o event loop do asyncio.

    Args:
        port: Porta para escutar (padrão SPEC: 8000)
        bind_host: Interface para bind (padrão: 0.0.0.0; produção: 127.0.0.1)
    """
    try:
        prometheus_start_server(port, addr=bind_host)
        logger.info("metrics_server_started", port=port, bind_host=bind_host)
    except Exception as exc:
        logger.warning(
            "metrics_server_failed",
            port=port,
            bind_host=bind_host,
            error_type=type(exc).__name__,
        )


def get_metrics() -> str:
    """
    Retorna as métricas formatadas como texto Prometheus.

    Usado pela dashboard API (FastAPI) que tem seu próprio servidor HTTP.

    Returns:
        String com todas métricas no formato Prometheus.
    """
    try:
        return generate_latest(REGISTRY).decode("utf-8")
    except Exception as exc:
        logger.error("metrics_generate_failed", error_type=type(exc).__name__)
        return ""


# --- Wrappers seguros (nunca quebram o bot) ---


def _safe_inc(
    counter: Counter,
    /,
    *,
    labels: dict[str, str] | None = None,
    amount: float = 1.0,
) -> None:
    """
    Wrapper seguro para incrementar Counter. Nunca lança exceção.
    """
    try:
        if labels:
            counter.labels(**labels).inc(amount)
        else:
            counter.inc(amount)
    except Exception as exc:
        logger.warning(
            "metrics_counter_inc_failed",
            metric=counter._name,  # type: ignore[attr-defined]
            error_type=type(exc).__name__,
        )


def _safe_set(
    gauge: Gauge,
    /,
    value: float,
    *,
    labels: dict[str, str] | None = None,
) -> None:
    """
    Wrapper seguro para definir Gauge. Nunca lança exceção.
    """
    try:
        if labels:
            gauge.labels(**labels).set(value)
        else:
            gauge.set(value)
    except Exception as exc:
        logger.warning(
            "metrics_gauge_set_failed",
            metric=gauge._name,  # type: ignore[attr-defined]
            error_type=type(exc).__name__,
        )


def _safe_observe(
    histogram: Histogram,
    /,
    value: float,
    *,
    labels: dict[str, str] | None = None,
) -> None:
    """
    Wrapper seguro para observar Histogram. Nunca lança exceção.
    """
    try:
        if labels:
            histogram.labels(**labels).observe(value)
        else:
            histogram.observe(value)
    except Exception as exc:
        logger.warning(
            "metrics_histogram_observe_failed",
            metric=histogram._name,  # type: ignore[attr-defined]
            error_type=type(exc).__name__,
        )


# --- Helpers de conveniência para os pontos de instrumentação ---


def record_signal_evaluated(symbol: str, timeframe: str) -> None:
    """Registra que uma avaliação de sinal foi executada."""
    _safe_inc(signals_evaluated_total, labels={"symbol": symbol, "timeframe": timeframe})


def record_signal_detected(
    symbol: str,
    timeframe: str,
    direction: Literal["long", "short"],
) -> None:
    """Registra que um sinal válido foi detectado."""
    _safe_inc(
        signals_total,
        labels={"symbol": symbol, "timeframe": timeframe, "direction": direction},
    )


def record_signal_rejected(symbol: str, reason: str) -> None:
    """Registra que um sinal foi rejeitado pelo RiskManager."""
    _safe_inc(signals_rejected_total, labels={"symbol": symbol, "reason": reason})


def record_trade_executed(
    symbol: str,
    direction: Literal["long", "short"],
    status: Literal["open", "win", "loss", "closed_manual"],
) -> None:
    """Registra que um trade foi executado ou fechado."""
    _safe_inc(trades_total, labels={"symbol": symbol, "direction": direction, "status": status})


def record_pnl_realized(symbol: str, pnl_usdt_value: float) -> None:
    """
    Registra PnL realizado.

    - Se positivo: incrementa pnl_realized_win_total
    - Se negativo: incrementa pnl_realized_loss_total com valor absoluto
    """
    if pnl_usdt_value > 0:
        _safe_inc(pnl_realized_win_total, labels={"symbol": symbol}, amount=pnl_usdt_value)
    elif pnl_usdt_value < 0:
        _safe_inc(pnl_realized_loss_total, labels={"symbol": symbol}, amount=abs(pnl_usdt_value))


def record_error(module: str, error_type: str) -> None:
    """Registra um erro capturado."""
    _safe_inc(errors_total, labels={"module": module, "error_type": error_type})


def record_api_request(endpoint: str, status: Literal["success", "error"]) -> None:
    """Registra uma chamada à API Binance."""
    _safe_inc(api_requests_total, labels={"endpoint": endpoint, "status": status})


def update_heartbeat() -> None:
    """Atualiza o heartbeat com timestamp atual."""
    _safe_set(heartbeat, time.time())


def update_positions_open(count: int) -> None:
    """Atualiza o gauge de posições abertas."""
    _safe_set(positions_open, float(count))


def update_pnl_snapshot(symbol: str | None, pnl: float) -> None:
    """
    Atualiza o snapshot de PnL (Gauge).

    Se symbol for None, usa "total" como label (geral).
    """
    effective_symbol = symbol or "total"
    _safe_set(pnl_usdt, pnl, labels={"symbol": effective_symbol})


def update_monitor_count(count: int) -> None:
    """Atualiza o número de TradingMonitors ativos."""
    _safe_set(monitor_count, float(count))


def observe_candle_latency(symbol: str, latency_seconds: float) -> None:
    """Registra latência de fetch_ohlcv()."""
    _safe_observe(candle_latency_seconds, latency_seconds, labels={"symbol": symbol})


def observe_tick_duration(
    symbol: str,
    timeframe: str,
    duration_seconds: float,
) -> None:
    """Registra duração de um _tick() completo."""
    _safe_observe(
        tick_duration_seconds,
        duration_seconds,
        labels={"symbol": symbol, "timeframe": timeframe},
    )
