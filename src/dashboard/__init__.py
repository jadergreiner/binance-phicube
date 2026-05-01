"""Módulo de painel de posições em tempo real (dashboard)."""

from src.dashboard.client import DashboardClient, DashboardClientError
from src.dashboard.updater import AdaptiveUpdater

__all__ = ["AdaptiveUpdater", "DashboardClient", "DashboardClientError"]
