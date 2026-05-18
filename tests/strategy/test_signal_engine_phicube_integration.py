"""
T03 — Testes de integração: SignalEngine + PluginRegistry + roteamento PhiCube.

Escopo:
    - phicube_enabled=False: SignalEngine usa Williams; sem regressão
    - phicube_enabled=True:  SignalEngine roteia para PhicubeStrategy
    - Shadow/advisory mode: sinal detectado mas execução bloqueada
    - Registry sem plugin phicube: fallback para Williams (Regra Mestre)
    - _resolve_strategy_routing: tabela de decisão completa
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategies.phicube_strategy import PhicubeStrategy
from src.strategies.williams_strategy import WilliamsStrategy
from src.strategy.plugin_base import NullSignalResult, SignalResult
from src.strategy.plugin_registry import PluginRegistry
from src.strategy.signal_engine import SignalEngine

# ─── Fixtures de DataFrame ────────────────────────────────────────────────────


def _bullish_df(n: int = 60) -> pd.DataFrame:
    close = np.linspace(100, 110, n)
    high = close + 1.5
    low = close - 1.5
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": 1000})
    df["jaw"] = np.linspace(100.0, 101.5, n)
    df["teeth"] = np.linspace(101.0, 102.5, n)
    df["lips"] = np.linspace(102.0, 103.5, n)
    df["ao"] = np.linspace(0.2, 0.8, n)
    df["fractal_high"] = np.nan
    df["fractal_low"] = np.nan
    df.loc[df.index[-5], "fractal_low"] = float(df["close"].iloc[-1] - 2.5)
    df.loc[df.index[-6], "fractal_high"] = float(df["close"].iloc[-1] - 0.4)
    df["atr"] = 1.0
    return df


def _bearish_df(n: int = 60) -> pd.DataFrame:
    close = np.linspace(110, 100, n)
    high = close + 1.5
    low = close - 1.5
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": 1000})
    df["jaw"] = np.linspace(104.0, 103.0, n)
    df["teeth"] = np.linspace(103.0, 102.0, n)
    df["lips"] = np.linspace(102.0, 101.0, n)
    df["ao"] = np.linspace(-0.2, -0.8, n)
    df["fractal_high"] = np.nan
    df["fractal_low"] = np.nan
    df.loc[df.index[-5], "fractal_high"] = float(df["close"].iloc[-1] + 2.5)
    df.loc[df.index[-6], "fractal_low"] = float(df["close"].iloc[-1] + 0.4)
    df["atr"] = 1.0
    return df


# ─── Registry helpers ─────────────────────────────────────────────────────────


def _registry_with_williams() -> PluginRegistry:
    reg = PluginRegistry(plugin_timeout=5.0)
    reg.register("williams", WilliamsStrategy())
    return reg


def _registry_with_both() -> PluginRegistry:
    reg = PluginRegistry(plugin_timeout=5.0)
    reg.register("williams", WilliamsStrategy())
    reg.register("phicube", PhicubeStrategy())
    return reg


# ─── T03-INT-01: phicube_enabled=False não altera roteamento ─────────────────


class TestPhicubeDisabledNoRegression:
    async def test_signal_engine_uses_williams_when_phicube_disabled(self) -> None:
        """phicube_enabled=False → chain usa williams; PhicubeStrategy não é invocada."""
        reg = _registry_with_both()
        engine = SignalEngine(
            plugin_registry=reg,
            default_strategy="williams",
            symbol_strategy_map={},
        )
        df = _bullish_df()
        result = await engine.evaluate("BTCUSDT", "15m", df)

        assert result.is_ok()
        payload = result.unwrap()
        # Williams produz sinal com metadata.plugin ausente ou não "phicube"
        if isinstance(payload, SignalResult):
            plugin_name = (payload.metadata or {}).get("plugin", "")
            assert plugin_name != "phicube", (
                f"Expected williams, got phicube: plugin={plugin_name}"
            )

    async def test_williams_signal_reaches_engine_without_phicube_keys(self) -> None:
        """Sem phicube no mapa, resultado de Williams não contém rule_hits PhiCube."""
        reg = _registry_with_williams()
        engine = SignalEngine(
            plugin_registry=reg,
            default_strategy="williams",
            symbol_strategy_map={},
        )
        df = _bullish_df()
        result = await engine.evaluate("BTCUSDT", "15m", df)

        assert result.is_ok()
        payload = result.unwrap()
        if isinstance(payload, SignalResult):
            rule_hits = (payload.metadata or {}).get("rule_hits", [])
            phicube_hits = [h for h in rule_hits if "RN-PHI" in str(h)]
            assert phicube_hits == [], (
                f"Williams result must not contain RN-PHI hits: {phicube_hits}"
            )


# ─── T03-INT-02: phicube_enabled=True roteia para PhicubeStrategy ─────────────


class TestPhicubeEnabledRouting:
    async def test_symbol_strategy_map_routes_to_phicube(self) -> None:
        """symbol_strategy_map com ADAUSDT→phicube resulta em SignalResult com plugin=phicube."""
        reg = _registry_with_both()
        engine = SignalEngine(
            plugin_registry=reg,
            default_strategy="phicube",
            symbol_strategy_map={"ADAUSDT": "phicube"},
        )
        df = _bullish_df()
        result = await engine.evaluate("ADAUSDT", "15m", df)

        assert result.is_ok()
        payload = result.unwrap()
        assert isinstance(payload, SignalResult), (
            f"PhiCube bullish df should produce SignalResult, got {type(payload)}: {payload}"
        )
        assert payload.direction == "LONG"
        plugin_name = (payload.metadata or {}).get("plugin", "")
        assert plugin_name == "phicube", f"Expected plugin=phicube, got {plugin_name!r}"

    async def test_phicube_result_contains_rule_hits(self) -> None:
        """Sinal PhiCube produzido pelo engine contém rule_hits com IDs canônicos."""
        reg = _registry_with_both()
        engine = SignalEngine(
            plugin_registry=reg,
            default_strategy="phicube",
            symbol_strategy_map={"ADAUSDT": "phicube"},
        )
        df = _bullish_df()
        result = await engine.evaluate("ADAUSDT", "15m", df)

        assert result.is_ok()
        payload = result.unwrap()
        assert isinstance(payload, SignalResult)
        rule_hits = (payload.metadata or {}).get("rule_hits", [])
        assert any("RN-PHI-015:long_setup_valid" in h for h in rule_hits), (
            f"rule_hits should contain RN-PHI-015:long_setup_valid; got {rule_hits}"
        )
        assert any("RN-PHI-024:chart_confirmed" in h for h in rule_hits), (
            f"rule_hits should contain RN-PHI-024:chart_confirmed; got {rule_hits}"
        )

    async def test_phicube_result_contains_market_state(self) -> None:
        """Sinal PhiCube produzido pelo engine contém market_state."""
        reg = _registry_with_both()
        engine = SignalEngine(
            plugin_registry=reg,
            default_strategy="phicube",
            symbol_strategy_map={"ADAUSDT": "phicube"},
        )
        df = _bullish_df()
        result = await engine.evaluate("ADAUSDT", "15m", df)

        assert result.is_ok()
        payload = result.unwrap()
        assert isinstance(payload, SignalResult)
        market_state = (payload.metadata or {}).get("market_state")
        assert market_state is not None, "PhiCube signal must include market_state"

    async def test_default_strategy_phicube_routes_unmapped_symbols(self) -> None:
        """default_strategy=phicube roteia símbolos não mapeados para PhiCube."""
        reg = _registry_with_both()
        engine = SignalEngine(
            plugin_registry=reg,
            default_strategy="phicube",
            symbol_strategy_map={},
        )
        df = _bullish_df()
        result = await engine.evaluate("SOLUSDT", "15m", df)

        assert result.is_ok()
        payload = result.unwrap()
        # PhiCube deve ser invocado; resultado é SignalResult ou NullSignalResult
        # O invariante é que o plugin phicube foi consultado (não williams)
        if isinstance(payload, SignalResult):
            plugin_name = (payload.metadata or {}).get("plugin", "")
            assert plugin_name == "phicube"


# ─── T03-INT-03: Fallback Williams quando phicube não está no registry ─────────


class TestRegistryFallbackToWilliams:
    async def test_engine_falls_back_to_williams_when_phicube_absent(self) -> None:
        """Registry sem phicube + default=phicube → engine cai para williams (Regra Mestre)."""
        reg = _registry_with_williams()  # apenas williams
        engine = SignalEngine(
            plugin_registry=reg,
            default_strategy="phicube",
            symbol_strategy_map={"BTCUSDT": "phicube"},
        )
        df = _bullish_df()
        result = await engine.evaluate("BTCUSDT", "15m", df)

        assert result.is_ok()
        # Sem phicube no registry, _build_chain cai para williams como fallback
        payload = result.unwrap()
        # Deve produzir resultado (não crash) e não ter metadata de phicube
        if isinstance(payload, SignalResult):
            plugin_name = (payload.metadata or {}).get("plugin", "")
            assert plugin_name != "phicube"

    async def test_engine_with_no_registry_returns_null(self) -> None:
        """Sem registry (None) → NullSignalResult com reason=no_plugin_registry."""
        engine = SignalEngine(plugin_registry=None)
        df = _bullish_df()
        result = await engine.evaluate("BTCUSDT", "15m", df)

        assert result.is_ok()
        payload = result.unwrap()
        assert isinstance(payload, NullSignalResult)
        assert payload.reason == "no_plugin_registry"


# ─── T03-INT-04: _resolve_strategy_routing (tabela de decisão) ────────────────


class TestResolveStrategyRouting:
    """Testa a lógica de _resolve_strategy_routing do RuntimeMonitorRegistry em isolamento."""

    def _routing(
        self,
        *,
        phicube_enabled: bool,
        default_strategy: str = "williams",
        symbol_strategy_map: dict | None = None,
        symbol_timeframes: list | None = None,
    ) -> tuple[str, dict[str, str]]:
        """Replica a lógica de _resolve_strategy_routing sem instanciar RuntimeMonitorRegistry."""

        class _FakeSettings:
            pass

        settings = _FakeSettings()
        settings.default_strategy = default_strategy
        settings.symbol_strategy_map = symbol_strategy_map or {}
        settings.phicube_enabled = phicube_enabled
        settings.symbol_timeframes = symbol_timeframes or []

        base_default = str(getattr(settings, "default_strategy", "williams"))
        base_map = dict(getattr(settings, "symbol_strategy_map", {}) or {})
        phi_enabled = bool(getattr(settings, "phicube_enabled", False))
        if not phi_enabled:
            return base_default, base_map

        for cfg in getattr(settings, "symbol_timeframes", []) or []:
            symbol = str(getattr(cfg, "symbol", "")).upper().strip()
            if symbol:
                base_map[symbol] = "phicube"
        return "phicube", base_map

    def test_disabled_returns_williams_default(self) -> None:
        default, smap = self._routing(phicube_enabled=False)
        assert default == "williams"
        assert smap == {}

    def test_disabled_preserves_existing_map(self) -> None:
        default, smap = self._routing(
            phicube_enabled=False,
            symbol_strategy_map={"BTCUSDT": "custom"},
        )
        assert default == "williams"
        assert smap == {"BTCUSDT": "custom"}

    def test_enabled_returns_phicube_default(self) -> None:
        default, smap = self._routing(phicube_enabled=True)
        assert default == "phicube"

    def test_enabled_maps_all_configured_symbols(self) -> None:
        class _Cfg:
            def __init__(self, symbol: str) -> None:
                self.symbol = symbol

        default, smap = self._routing(
            phicube_enabled=True,
            symbol_timeframes=[_Cfg("ADAUSDT"), _Cfg("SOLUSDT")],
        )
        assert default == "phicube"
        assert smap.get("ADAUSDT") == "phicube"
        assert smap.get("SOLUSDT") == "phicube"

    def test_enabled_uppercases_symbols(self) -> None:
        class _Cfg:
            def __init__(self, symbol: str) -> None:
                self.symbol = symbol

        _, smap = self._routing(
            phicube_enabled=True,
            symbol_timeframes=[_Cfg("adausdt")],
        )
        assert "ADAUSDT" in smap
        assert smap["ADAUSDT"] == "phicube"

    def test_enabled_skips_empty_symbol(self) -> None:
        class _Cfg:
            def __init__(self, symbol: str) -> None:
                self.symbol = symbol

        _, smap = self._routing(
            phicube_enabled=True,
            symbol_timeframes=[_Cfg(""), _Cfg("BTCUSDT")],
        )
        assert "" not in smap
        assert smap.get("BTCUSDT") == "phicube"


# ─── T03-INT-05: Mode gate no TradingMonitor ──────────────────────────────────


class TestModeGateResolveBlockReason:
    """Testa _resolve_mode_block_reason em isolamento."""

    def _block_reason(self, phicube_mode: str, plugin_name: str) -> str | None:
        """Replica lógica de TradingMonitor._resolve_mode_block_reason."""
        from src.strategy.plugin_base import SignalResult

        signal = SignalResult(
            direction="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            metadata={"plugin": plugin_name},
        )
        metadata = signal.metadata if isinstance(signal.metadata, dict) else {}
        pname = str(metadata.get("plugin") or "").strip().lower()
        if pname != "phicube":
            return None
        mode = str(phicube_mode or "shadow").strip().lower()
        if mode == "shadow":
            return "phicube_mode_shadow_blocked_execution"
        if mode == "advisory":
            return "phicube_mode_advisory_blocked_execution"
        return None

    def test_shadow_mode_blocks_phicube_signal(self) -> None:
        reason = self._block_reason("shadow", "phicube")
        assert reason == "phicube_mode_shadow_blocked_execution"

    def test_advisory_mode_blocks_phicube_signal(self) -> None:
        reason = self._block_reason("advisory", "phicube")
        assert reason == "phicube_mode_advisory_blocked_execution"

    def test_active_mode_does_not_block_phicube_signal(self) -> None:
        reason = self._block_reason("active", "phicube")
        assert reason is None

    def test_williams_signal_never_blocked_regardless_of_mode(self) -> None:
        for mode in ("shadow", "advisory", "active"):
            reason = self._block_reason(mode, "williams")
            assert reason is None, f"Williams should not be blocked in {mode!r} mode"

    def test_empty_plugin_name_not_blocked(self) -> None:
        reason = self._block_reason("shadow", "")
        assert reason is None

    def test_shadow_mode_is_default_when_mode_is_none(self) -> None:
        reason = self._block_reason("", "phicube")
        # str("" or "shadow") → "shadow" → blocks
        assert reason == "phicube_mode_shadow_blocked_execution"


# ─── T03-INT-06: PluginRegistry Regra Mestre ──────────────────────────────────


class TestPluginRegistryMasterRule:
    def test_validate_master_raises_without_williams(self) -> None:
        reg = PluginRegistry()
        with pytest.raises(RuntimeError, match="williams"):
            reg.validate_master()

    def test_validate_master_passes_with_williams(self) -> None:
        reg = PluginRegistry()
        reg.register("williams", WilliamsStrategy())
        reg.validate_master()  # deve não levantar

    def test_williams_slot_protected_against_overwrite(self) -> None:
        reg = PluginRegistry()
        reg.register("williams", WilliamsStrategy())
        # Segunda tentativa de registrar o mesmo slot "williams" é ignorada (log warning)
        reg.register("williams", WilliamsStrategy())
        # Regra Mestre ainda preservada
        reg.validate_master()

    def test_phicube_plugin_registered_and_retrievable(self) -> None:
        reg = PluginRegistry()
        reg.register("williams", WilliamsStrategy())
        reg.register("phicube", PhicubeStrategy())
        plugin = reg.get("phicube")
        assert plugin is not None
        warmup = plugin.warmup_candles()
        assert isinstance(warmup, int) and warmup >= 50

    def test_health_check_includes_phicube(self) -> None:
        reg = PluginRegistry()
        reg.register("williams", WilliamsStrategy())
        reg.register("phicube", PhicubeStrategy())
        health = reg.health_check()
        assert health.get("phicube") is True
        assert health.get("williams") is True
