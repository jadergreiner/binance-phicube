"""
Testes SPEC_033 — Plugin Base + PluginRegistry (TEST_033_01 a 06).

Verifica:
    - SignalResult / NullSignalResult (Null Object Pattern)
    - StrategyPlugin (Template Method)
    - PluginRegistry (Registry Pattern)
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.strategy.plugin_base import (
    NullSignalResult,
    SignalResult,
    StrategyPlugin,
)
from src.strategy.plugin_registry import PluginRegistry

# ─── TEST_033_01: SignalResult / NullSignalResult ─────────────────────────────


class TestSignalResult:
    def test_signal_result_is_truthy(self) -> None:
        sr = SignalResult(direction="LONG", entry_price=100, stop_loss=90, take_profit=120)
        assert bool(sr) is True

    def test_null_signal_result_is_falsy(self) -> None:
        nsr = NullSignalResult(reason="test")
        assert bool(nsr) is False

    def test_null_signal_result_short_circuits_if_block(self) -> None:
        nsr = NullSignalResult(reason="not_ready")
        if nsr:
            pytest.fail("NullSignalResult should be falsy in if-block")
        # If we got here, the short-circuit works

    def test_signal_result_enters_if_block(self) -> None:
        sr = SignalResult(direction="SHORT", entry_price=50, stop_loss=55, take_profit=45)
        entered = False
        if sr:
            entered = True
        assert entered is True

    def test_signal_result_stores_fields(self) -> None:
        sr = SignalResult(
            direction="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            metadata={"confidence": 0.75},
        )
        assert sr.direction == "LONG"
        assert sr.entry_price == 100.0
        assert sr.stop_loss == 95.0
        assert sr.take_profit == 110.0
        assert sr.metadata == {"confidence": 0.75}

    def test_null_signal_result_stores_reason(self) -> None:
        nsr = NullSignalResult(reason="insufficient_candles")
        assert nsr.reason == "insufficient_candles"

    def test_signal_result_frozen(self) -> None:
        sr = SignalResult(direction="LONG", entry_price=100, stop_loss=90, take_profit=120)
        with pytest.raises(AttributeError):
            sr.direction = "SHORT"  # type: ignore[misc]


# ─── TEST_033_02: Template Method ─────────────────────────────────────────────


class _MockPlugin(StrategyPlugin):
    """Plugin que registra ordem de chamada dos hooks do Template Method."""

    def __init__(self, risk_reward_ratio: float = 2.0) -> None:
        super().__init__(risk_reward_ratio)
        self._plugin_name = "mock"
        self.hook_order: list[str] = []

    def warmup_candles(self) -> int:
        return 10

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        self.hook_order.append("_compute_indicators")
        df_out = df.copy()
        df_out["jaw"] = 105.0
        df_out["teeth"] = 103.0
        df_out["lips"] = 101.0
        df_out["ao"] = 1.5
        return df_out

    def _check_conditions(self, symbol: str, timeframe: str, df: pd.DataFrame) -> dict | None:
        self.hook_order.append("_check_conditions")
        return {
            "direction": "LONG",
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "metadata": {},
        }

    def _calculate_targets(self, conditions: dict, df: pd.DataFrame) -> dict:
        self.hook_order.append("_calculate_targets")
        return {
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 110.0,
        }

    def _calculate_confidence(self, conditions: dict, df: pd.DataFrame) -> float:
        self.hook_order.append("_calculate_confidence")
        return 0.75


class TestTemplateMethod:
    async def test_evaluate_calls_hooks_in_order(self) -> None:
        """Template Method chama hooks na ordem correta."""
        plugin = _MockPlugin()
        df = pd.DataFrame({"close": [100.0] * 50, "high": [105.0] * 50, "low": [95.0] * 50})
        result = await plugin.evaluate("BTCUSDT", "15m", df)
        expected_order = [
            "_compute_indicators",
            "_check_conditions",
            "_calculate_targets",
            "_calculate_confidence",
        ]
        assert plugin.hook_order == expected_order, (
            f"Expected hook order {expected_order}, got {plugin.hook_order}"
        )
        assert isinstance(result, SignalResult)
        assert result.direction == "LONG"
        assert result.metadata is not None
        assert result.metadata.get("confidence") == 0.75

    async def test_conditions_none_returns_null_signal_result(self) -> None:
        """Quando _check_conditions retorna None, evaluate retorna NullSignalResult."""

        class _NoSignalPlugin(_MockPlugin):
            def _check_conditions(
                self, symbol: str, timeframe: str, df: pd.DataFrame
            ) -> dict | None:
                return None

        plugin = _NoSignalPlugin()
        df = pd.DataFrame({"close": [100.0] * 50, "high": [105.0] * 50, "low": [95.0] * 50})
        result = await plugin.evaluate("BTCUSDT", "15m", df)
        assert isinstance(result, NullSignalResult)
        assert result.reason == "conditions_not_met"

    async def test_exception_in_hook_returns_null_signal_result(self) -> None:
        """Exceção em qualquer hook é capturada e retorna NullSignalResult."""

        class _FailingPlugin(_MockPlugin):
            def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
                raise ValueError("indicator error")

        plugin = _FailingPlugin()
        df = pd.DataFrame({"close": [100.0] * 50})
        result = await plugin.evaluate("BTCUSDT", "15m", df)
        assert isinstance(result, NullSignalResult)
        assert result.reason == "evaluation_error"

    def test_init_subclass_guard_raises_on_missing_super(self) -> None:
        """Plugin que não chama super().__init__() no __init__ levanta TypeError."""

        class _BadPlugin(StrategyPlugin):
            def __init__(self) -> None:  # noqa: super-init-not-called
                pass  # intentionally skipping super().__init__

            def warmup_candles(self) -> int:
                return 10

            def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
                return df

            def _check_conditions(
                self, symbol: str, timeframe: str, df: pd.DataFrame
            ) -> dict | None:
                return None

            def _calculate_targets(self, conditions: dict, df: pd.DataFrame) -> dict:
                return {}

            def _calculate_confidence(self, conditions: dict, df: pd.DataFrame) -> float:
                return 0.0

        with pytest.raises(TypeError, match="must call super\\(\\)\\.__init__"):
            _BadPlugin()


# ─── TEST_033_03: PluginRegistry register / get / wrap ────────────────────────


class _MinimalPlugin(StrategyPlugin):
    def __init__(self, risk_reward_ratio: float = 2.0) -> None:
        super().__init__(risk_reward_ratio)
        self._plugin_name = "minimal"

    def warmup_candles(self) -> int:
        return 20

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        df_out["jaw"] = 0
        df_out["teeth"] = 0
        df_out["lips"] = 0
        df_out["ao"] = 0
        return df_out

    def _check_conditions(self, symbol: str, timeframe: str, df: pd.DataFrame) -> dict | None:
        return None

    def _calculate_targets(self, conditions: dict, df: pd.DataFrame) -> dict:
        return {}

    def _calculate_confidence(self, conditions: dict, df: pd.DataFrame) -> float:
        return 0.0


class TestPluginRegistry:
    def test_register_and_get(self) -> None:
        registry = PluginRegistry(plugin_timeout=30.0)
        plugin = _MinimalPlugin()
        registry.register("test_strat", plugin)
        retrieved = registry.get("test_strat")
        assert retrieved is not None
        # get() returns wrapped instance
        assert retrieved.warmup_candles() == 20

    def test_unknown_plugin_returns_none(self) -> None:
        registry = PluginRegistry()
        assert registry.get("nonexistent") is None

    def test_available_excludes_williams(self) -> None:
        registry = PluginRegistry()
        registry.register("williams", _MinimalPlugin())
        registry.register("custom", _MinimalPlugin())
        assert "williams" not in registry.available
        assert "custom" in registry.available

    def test_all_returns_all_plugins(self) -> None:
        registry = PluginRegistry()
        registry.register("alpha", _MinimalPlugin())
        registry.register("beta", _MinimalPlugin())
        assert set(registry.all.keys()) == {"alpha", "beta"}

    def test_williams_slot_is_protected(self) -> None:
        registry = PluginRegistry()
        p1 = _MinimalPlugin()
        p2 = _MinimalPlugin()
        registry.register("williams", p1)
        # Tentativa de sobrescrever williams é ignorada
        registry.register("williams", p2)
        retrieved = registry.get("williams")
        assert retrieved is not None
        # O wrapped_plugin deve ser o p1 original, não p2
        from src.strategy.plugin_decorator import PluginDecorator

        assert isinstance(retrieved, PluginDecorator)
        assert retrieved.wrapped_plugin is p1

    def test_register_wraps_with_decorators(self) -> None:
        """Plugin registrado é instância de PluginDecorator (wrapper)."""
        from src.strategy.plugin_decorator import PluginDecorator

        registry = PluginRegistry()
        registry.register("test", _MinimalPlugin())
        retrieved = registry.get("test")
        assert isinstance(retrieved, PluginDecorator)
        # wrapped_plugin deve ser o plugin real
        assert isinstance(retrieved.wrapped_plugin, _MinimalPlugin)

    def test_register_overwrite_logs_warning(self) -> None:
        """Registrar mesmo nome duas vezes loga warning."""

        registry = PluginRegistry()
        registry.register("custom", _MinimalPlugin())
        # Segunda chamada não deve levantar exceção
        registry.register("custom", _MinimalPlugin())
        # Apenas verifica que não crasha; warning é logado internamente
        assert "custom" in registry.all


# ─── TEST_033_04: discover_and_register_all ───────────────────────────────────


class TestDiscoverAndRegister:
    def test_discover_no_entry_points_returns_gracefully(self) -> None:
        """Sem entry_points, discover_and_register_all não levanta exceção por padrão."""
        registry = PluginRegistry()
        # Sem entry_points configurados, apenas loga warning
        # e retorna sem plugins
        registry.discover_and_register_all()
        assert len(registry.all) == 0

    def test_discover_with_mock_entry_point(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Com entry_point mock, descobre e registra plugin."""
        registry = PluginRegistry()

        class _MockEntryPoint:
            name = "mock_strat"

            def load(self) -> type:
                return _MinimalPlugin

        class _MockEntryPoints:
            @staticmethod
            def select(*args: str, **kwargs: str) -> list:  # noqa: ARG004
                return [_MockEntryPoint()]

        monkeypatch.setattr(
            "importlib.metadata.entry_points",
            lambda group=None: [_MockEntryPoint()],  # type: ignore[arg-type]
        )

        registry.discover_and_register_all()
        assert "mock_strat" in registry.all


# ─── TEST_033_05: health_check ────────────────────────────────────────────────


class TestHealthCheck:
    def test_healthy_plugin_returns_true(self) -> None:
        registry = PluginRegistry()
        registry.register("good", _MinimalPlugin())
        status = registry.health_check()
        assert status.get("good") is True

    def test_failing_plugin_returns_false(self) -> None:
        class _BrokenPlugin(_MinimalPlugin):
            def warmup_candles(self) -> int:
                raise RuntimeError("broken")

        registry = PluginRegistry()
        registry.register("broken", _BrokenPlugin())
        status = registry.health_check()
        assert status.get("broken") is False

    def test_empty_registry_health(self) -> None:
        registry = PluginRegistry()
        assert registry.health_check() == {}


# ─── TEST_033_06: validate_master ─────────────────────────────────────────────


class TestValidateMaster:
    def test_validate_master_passes_when_williams_present(self) -> None:
        registry = PluginRegistry()
        registry.register("williams", _MinimalPlugin())
        registry.validate_master()  # não deve levantar exceção

    def test_validate_master_raises_when_williams_missing(self) -> None:
        registry = PluginRegistry()
        registry.register("custom", _MinimalPlugin())
        with pytest.raises(RuntimeError, match="Regra Mestre"):
            registry.validate_master()

    def test_validate_master_raises_on_empty_registry(self) -> None:
        registry = PluginRegistry()
        with pytest.raises(RuntimeError, match="Regra Mestre"):
            registry.validate_master()
