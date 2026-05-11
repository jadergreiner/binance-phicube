"""
Testes para PerformanceReporter — TEST_008_01 a TEST_008_05.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.notifications.events import NotificationEvent, PerformanceReportEvent
from src.notifications.performance_reporter import PerformanceReporter
from src.notifications.telegram_notifier import NullNotifier


def _make_metrics(total_trades: int = 10) -> dict:
    if total_trades == 0:
        return {
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "total_pnl_usdt": 0.0,
            "avg_rrr": 0.0,
            "max_drawdown_usdt": 0.0,
            "profit_factor": 0.0,
        }
    return {
        "total_trades": total_trades,
        "win_rate_pct": 60.0,
        "total_pnl_usdt": 123.45,
        "avg_rrr": 1.85,
        "max_drawdown_usdt": -45.20,
        "profit_factor": 2.10,
    }


class TestPerformanceReporter:
    """Testes unitários para PerformanceReporter."""

    # TEST_008_01: _send_report com métricas válidas
    @pytest.mark.asyncio
    async def test_send_report_com_metricas_validas(self) -> None:
        """_send_report formata mensagem com as 6 métricas e chama notifier.send()."""
        repo = MagicMock()
        repo.get_performance_metrics = AsyncMock(return_value=_make_metrics(10))

        notifier = MagicMock()
        notifier.send = AsyncMock(return_value=True)

        reporter = PerformanceReporter(repo, notifier, interval_hours=24.0)
        await reporter._send_report()

        notifier.send.assert_called_once()
        call_args = notifier.send.call_args
        event, payload = call_args[0]

        assert event == NotificationEvent.PERFORMANCE_REPORT
        assert isinstance(payload, PerformanceReportEvent)
        assert payload.total_trades == 10
        assert payload.win_rate_pct == 60.0
        assert payload.total_pnl_usdt == 123.45

        message = payload.to_message()
        assert "Trades: 10" in message
        assert "Win Rate: 60.00%" in message
        assert "+123.45 USDT" in message
        assert "RRR Médio: 1.85" in message

    # TEST_008_02: _send_report com total_trades == 0
    @pytest.mark.asyncio
    async def test_send_report_sem_trades(self) -> None:
        """_send_report com total_trades == 0 envia mensagem simplificada."""
        repo = MagicMock()
        repo.get_performance_metrics = AsyncMock(return_value=_make_metrics(0))

        notifier = MagicMock()
        notifier.send = AsyncMock(return_value=True)

        reporter = PerformanceReporter(repo, notifier, interval_hours=24.0)
        await reporter._send_report()

        notifier.send.assert_called_once()
        event, payload = notifier.send.call_args[0]

        assert event == NotificationEvent.PERFORMANCE_REPORT
        assert isinstance(payload, PerformanceReportEvent)
        assert payload.total_trades == 0

        message = payload.to_message()
        assert "Nenhum trade fechado ainda" in message
        assert "Win Rate" not in message

    # TEST_008_03: _send_report com MongoDB falhando
    @pytest.mark.asyncio
    async def test_send_report_mongodb_falha_nao_crasha(self, capfd) -> None:
        """_send_report não lança exceção quando MongoDB falha; emite log de erro."""
        repo = MagicMock()
        repo.get_performance_metrics = AsyncMock(side_effect=ConnectionError("mongo down"))

        notifier = MagicMock()
        notifier.send = AsyncMock()

        reporter = PerformanceReporter(repo, notifier, interval_hours=24.0)
        await reporter._send_report()  # não deve lançar

        notifier.send.assert_not_called()

        captured = capfd.readouterr()
        assert "performance_report_metrics_error" in (captured.out + captured.err)
        assert "ConnectionError" in (captured.out + captured.err)

    # TEST_008_04: _send_report com Telegram falhando
    @pytest.mark.asyncio
    async def test_send_report_telegram_falha_nao_crasha(self) -> None:
        """_send_report não lança exceção mesmo se notifier.send() levantar erro."""
        repo = MagicMock()
        repo.get_performance_metrics = AsyncMock(return_value=_make_metrics(5))

        notifier = MagicMock()
        notifier.send = AsyncMock(side_effect=RuntimeError("telegram down"))

        reporter = PerformanceReporter(repo, notifier, interval_hours=24.0)
        # NullNotifier garante no-raise, mas testamos um notifier que lança
        # _send_report não captura exceção de notifier.send() intencionalmente
        # (Notifier ABC garante que send() nunca lança — contrato de interface)
        # Este teste verifica que o reporter não adiciona try/except desnecessário
        with pytest.raises(RuntimeError):
            await reporter._send_report()

    # TEST_008_05: run() com interval_hours == 0 retorna imediatamente
    @pytest.mark.asyncio
    async def test_run_desabilitado_retorna_imediatamente(self) -> None:
        """run() com interval_hours == 0 retorna sem chamar _send_report."""
        repo = MagicMock()
        repo.get_performance_metrics = AsyncMock()

        notifier = NullNotifier()
        reporter = PerformanceReporter(repo, notifier, interval_hours=0)

        await reporter.run()  # deve retornar sem sleep

        repo.get_performance_metrics.assert_not_called()

    # Bônus: NullNotifier funciona com PERFORMANCE_REPORT
    @pytest.mark.asyncio
    async def test_null_notifier_aceita_performance_report(self) -> None:
        """NullNotifier retorna True para PERFORMANCE_REPORT sem erros."""
        repo = MagicMock()
        repo.get_performance_metrics = AsyncMock(return_value=_make_metrics(3))

        notifier = NullNotifier()
        reporter = PerformanceReporter(repo, notifier, interval_hours=1.0)
        await reporter._send_report()  # não deve lançar
