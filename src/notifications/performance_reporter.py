"""
Relatório periódico de performance — envia métricas agregadas via Telegram
em intervalos configuráveis.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from src.monitoring.logger import get_logger
from src.notifications.events import NotificationEvent, PerformanceReportEvent
from src.notifications.notifier import Notifier
from src.storage.repository import MongoRepository

logger = get_logger(__name__)


class PerformanceReporter:
    """Envia relatório periódico de performance via notifier configurado."""

    def __init__(
        self,
        repository: MongoRepository,
        notifier: Notifier,
        interval_hours: float,
    ) -> None:
        self._repository = repository
        self._notifier = notifier
        self._interval_hours = interval_hours

    async def run(self) -> None:
        """Loop infinito com sleep entre relatórios. Retorna imediatamente se interval_hours == 0."""  # noqa: E501
        if self._interval_hours <= 0:
            logger.info("performance_reporter_disabled")
            return

        logger.info("performance_reporter_started", interval_hours=self._interval_hours)

        while True:
            await asyncio.sleep(self._interval_hours * 3600)
            try:
                await self._send_report()
            except asyncio.CancelledError:
                raise

    async def _send_report(self) -> None:
        """Obtém métricas, formata e envia via notifier. Nunca lança exceção."""
        try:
            metrics = await self._repository.get_performance_metrics()
        except Exception as exc:
            logger.error(
                "performance_report_metrics_error",
                error_type=type(exc).__name__,
            )
            return

        payload = PerformanceReportEvent(
            total_trades=metrics.get("total_trades", 0),
            win_rate_pct=metrics.get("win_rate_pct", 0.0),
            total_pnl_usdt=metrics.get("total_pnl_usdt", 0.0),
            avg_rrr=metrics.get("avg_rrr", 0.0),
            max_drawdown_usdt=metrics.get("max_drawdown_usdt", 0.0),
            profit_factor=metrics.get("profit_factor", 0.0),
            timestamp=datetime.now(UTC),
        )

        await self._notifier.send(NotificationEvent.PERFORMANCE_REPORT, payload)
        logger.info("performance_report_sent", total_trades=payload.total_trades)
