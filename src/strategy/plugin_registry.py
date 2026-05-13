"""
PluginRegistry — Registro, descoberta e ciclo de vida de plugins de estratégia.

Padrões: Registry + Chain of Responsibility.

A Regra Mestre garante que WilliamsStrategy está sempre disponível
como fallback imutável (slot 'williams').
"""

from __future__ import annotations

from src.monitoring.logger import get_logger
from src.strategy.plugin_base import StrategyPlugin
from src.strategy.plugin_decorator import (
    MetricsDecorator,
    TimeoutDecorator,
    ValidationDecorator,
)

logger = get_logger(__name__)

_WILLIAMS_SLOT = "williams"


class PluginRegistry:
    def __init__(self, plugin_timeout: float = 30.0) -> None:
        self._plugins: dict[str, StrategyPlugin] = {}
        self._plugin_timeout = plugin_timeout

    def discover_and_register_all(self) -> None:
        try:
            from importlib.metadata import entry_points

            eps = entry_points(group="phicube.strategies")
        except Exception as exc:
            logger.warning("plugin_discovery_failed", error_type=type(exc).__name__)
            eps = []

        if not eps:
            logger.warning("no_entry_points_found")
            return

        any_registered = False
        for ep in eps:
            try:
                plugin_class = ep.load()
                plugin = plugin_class()
                self.register(ep.name, plugin)
                any_registered = True
                logger.info("plugin_registered", name=ep.name)
            except Exception as exc:
                logger.warning(
                    "plugin_register_failed",
                    name=ep.name,
                    error_type=type(exc).__name__,
                )

        if not any_registered:
            raise RuntimeError("no_plugins_discovered")

    def register(self, name: str, plugin: StrategyPlugin, /) -> None:
        if name == _WILLIAMS_SLOT:
            if _WILLIAMS_SLOT in self._plugins:
                logger.warning(
                    "plugin_slot_protected",
                    slot=_WILLIAMS_SLOT,
                    action="skipped",
                )
                return
        if name in self._plugins:
            logger.warning("plugin_overwritten", name=name)

        wrapped = self._wrap_plugin(plugin)
        self._plugins[name] = wrapped

    def _wrap_plugin(self, plugin: StrategyPlugin) -> StrategyPlugin:
        wrapped: StrategyPlugin = MetricsDecorator(plugin)
        wrapped = ValidationDecorator(wrapped)
        wrapped = TimeoutDecorator(wrapped, timeout=self._plugin_timeout)
        return wrapped

    def validate_master(self) -> None:
        if _WILLIAMS_SLOT not in self._plugins:
            raise RuntimeError(f"Regra Mestre: plugin '{_WILLIAMS_SLOT}' não registrado")

    def get(self, name: str) -> StrategyPlugin | None:
        return self._plugins.get(name)

    @property
    def available(self) -> list[str]:
        return [n for n in self._plugins if n != _WILLIAMS_SLOT]

    @property
    def all(self) -> dict[str, StrategyPlugin]:
        return dict(self._plugins)

    def health_check(self) -> dict[str, bool]:
        result: dict[str, bool] = {}
        for name, plugin in self._plugins.items():
            try:
                warmup = plugin.warmup_candles()
                result[name] = isinstance(warmup, int) and warmup > 0
            except Exception:
                result[name] = False
        return result
