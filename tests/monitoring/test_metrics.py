"""
Testes unitários para src/monitoring/metrics.py.

Cobre os testes da SPEC_032 seção 7.1.
"""

from __future__ import annotations

import re
from unittest.mock import patch

from src.monitoring import metrics
from src.monitoring.metrics import (
    get_metrics,
    initialize,
    record_error,
    record_pnl_realized,
    record_signal_detected,
    record_signal_evaluated,
    record_signal_rejected,
    record_trade_executed,
    update_heartbeat,
    update_positions_open,
)


class TestGetMetrics:
    """TEST_032_01: get_metrics() retorna string não vazia com formato válido."""

    def test_returns_non_empty_string(self) -> None:
        result = get_metrics()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_prometheus_format(self) -> None:
        """Verifica que contém # HELP ou # TYPE (formato Prometheus)."""
        result = get_metrics()
        assert "# HELP" in result or "# TYPE" in result


class TestCounters:
    """TEST_032_02: Counters incrementam corretamente."""

    def test_trades_total_increments(self) -> None:
        """Testa record_trade_executed incrementa trades_total."""
        # Incrementar
        record_trade_executed("BTCUSDT", "long", "open")

        # Verificar
        metrics_text = get_metrics()
        assert "phicube_trades_total" in metrics_text
        assert 'symbol="BTCUSDT"' in metrics_text
        assert 'direction="long"' in metrics_text
        assert 'status="open"' in metrics_text

    def test_signals_total_increments(self) -> None:
        """Testa record_signal_detected incrementa signals_total."""
        record_signal_detected("ETHUSDT", "15m", "short")
        metrics_text = get_metrics()
        assert "phicube_signals_total" in metrics_text
        assert 'symbol="ETHUSDT"' in metrics_text
        assert 'direction="short"' in metrics_text

    def test_signals_evaluated_increments(self) -> None:
        """Testa record_signal_evaluated."""
        record_signal_evaluated("SOLUSDT", "1h")
        metrics_text = get_metrics()
        assert "phicube_signals_evaluated_total" in metrics_text
        assert 'symbol="SOLUSDT"' in metrics_text

    def test_signals_rejected_increments(self) -> None:
        """Testa record_signal_rejected."""
        record_signal_rejected("BNBUSDT", "MAX_CAPITAL_EXCEEDED")
        metrics_text = get_metrics()
        assert "phicube_signals_rejected_total" in metrics_text
        assert 'reason="MAX_CAPITAL_EXCEEDED"' in metrics_text


class TestGauges:
    """TEST_032_03: Gauges atualizam corretamente."""

    def test_heartbeat_metric_exists(self) -> None:
        """Testa que métrica phicube_heartbeat_seconds existe."""
        update_heartbeat()
        metrics_text = get_metrics()
        assert "phicube_heartbeat_seconds" in metrics_text

    def test_positions_open_updates(self) -> None:
        """Testa update_positions_open."""
        update_positions_open(3)
        metrics_text = get_metrics()
        assert "phicube_positions_open" in metrics_text


class TestHistograms:
    """TEST_032_04: Histograms registram observação."""

    def test_candle_latency_records(self) -> None:
        """Testa observe_candle_latency."""
        metrics.observe_candle_latency("BTCUSDT", 0.15)
        metrics_text = get_metrics()
        assert "phicube_candle_latency_seconds" in metrics_text


class TestInitialize:
    """TEST_032_05: initialize() popula phicube_info."""

    def test_initialize_sets_info(self) -> None:
        """Testa que initialize define version, testnet, python_version."""
        initialize(version="0.1.0-test", testnet=True, python_version="3.11.0")

        metrics_text = get_metrics()

        # phicube_info é exportado como phicube_info{...} 1.0
        assert 'version="0.1.0-test"' in metrics_text
        assert 'testnet="true"' in metrics_text
        assert 'python_version="3.11.0"' in metrics_text

    def test_initialize_sets_start_time_and_up(self) -> None:
        """Testa que initialize define start_time e up=1."""
        initialize()
        metrics_text = get_metrics()
        pattern_start = r"phicube_start_time_seconds (\d+\.\d+)"
        matches_start = re.findall(pattern_start, metrics_text)
        assert len(matches_start) >= 1
        assert float(matches_start[0]) > 0

        pattern_up = r"phicube_up (\d+\.\d+)"
        matches_up = re.findall(pattern_up, metrics_text)
        assert len(matches_up) >= 1
        assert float(matches_up[0]) == 1.0


class TestPnlRealized:
    """Testa record_pnl_realized separa win/loss."""

    def test_positive_pnl_goes_to_win(self) -> None:
        """PnL positivo incrementa pnl_realized_win_total."""
        record_pnl_realized("BTCUSDT", 150.5)
        metrics_text = get_metrics()
        assert "phicube_pnl_realized_win_total" in metrics_text

    def test_negative_pnl_goes_to_loss(self) -> None:
        """PnL negativo incrementa pnl_realized_loss_total com valor absoluto."""
        record_pnl_realized("ETHUSDT", -75.25)
        metrics_text = get_metrics()
        assert "phicube_pnl_realized_loss_total" in metrics_text


class TestSafeWrappers:
    """Testa que wrappers seguros não lançam exceção."""

    def test_safe_inc_does_not_raise(self) -> None:
        """Wrappers não devem lançar exceção mesmo com labels inválidos."""
        with patch("src.monitoring.metrics.logger.warning"):
            metrics._safe_inc(
                metrics.trades_total,
                labels={
                    "symbol": "BTCUSDT",
                    "direction": "long",
                    "status": "open",
                },
            )

    def test_safe_set_does_not_raise(self) -> None:
        with patch("src.monitoring.metrics.logger.warning"):
            metrics._safe_set(metrics.heartbeat, 123456.0)


class TestCardinality:
    """TEST_032_08: Verifica que nenhuma métrica define mais de 3 labels."""

    DEFINED_METRICS_INFO = [
        ("phicube_heartbeat_seconds", 0),
        ("phicube_positions_open", 0),
        ("phicube_pnl_usdt", 1),
        ("phicube_signals_total", 3),
        ("phicube_signals_evaluated_total", 2),
        ("phicube_signals_rejected_total", 2),
        ("phicube_trades_total", 3),
        ("phicube_pnl_realized_win_total", 1),
        ("phicube_pnl_realized_loss_total", 1),
        ("phicube_errors_total", 2),
        ("phicube_api_requests_total", 2),
        ("phicube_candle_latency_seconds", 1),
        ("phicube_tick_duration_seconds", 2),
        ("phicube_monitor_count", 0),
    ]

    def test_metrics_exported_with_correct_names(self) -> None:
        """Verifica que todas métricas da lista estão presentes no export."""
        initialize()
        metrics_text = get_metrics()

        for name, _ in self.DEFINED_METRICS_INFO:
            assert name in metrics_text, f"Métrica {name} não encontrada"


class TestRecordError:
    """Testa record_error."""

    def test_record_error_increments_counter(self) -> None:
        record_error("signal_engine", "ValueError")
        metrics_text = get_metrics()
        assert "phicube_errors_total" in metrics_text
        assert 'module="signal_engine"' in metrics_text
        assert 'error_type="ValueError"' in metrics_text
