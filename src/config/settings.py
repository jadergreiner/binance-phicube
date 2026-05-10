from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any, cast

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_COMMODITIES = frozenset({"XPTUSDT", "COPPERUSDT"})


@dataclass(frozen=True)
class SymbolConfig:
    """Configuração de um par de trading: símbolo, timeframe e alavancagem."""

    symbol: str
    timeframe: str
    leverage: int

    @classmethod
    def from_triplet(cls, triplet: str) -> SymbolConfig:
        """Parse 'BTCUSDT:15m:5' → SymbolConfig."""
        parts = triplet.strip().split(":")
        if len(parts) != 3:
            raise ValueError(
                f"Triplet inválido: {triplet!r} — formato esperado: SYMBOL:TIMEFRAME:LEVERAGE"
            )
        symbol, timeframe, leverage_str = parts
        if not leverage_str.isdigit():
            raise ValueError(f"Leverage inválida em triplet: {triplet!r}")
        leverage = int(leverage_str)
        if leverage <= 0 or leverage > 20:
            raise ValueError(
                f"Leverage inválida em triplet: {triplet!r}. "
                "Valor permitido: inteiro entre 1 e 20."
            )
        return cls(symbol=symbol.upper(), timeframe=timeframe, leverage=leverage)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Binance
    binance_api_key: str = Field(..., description="Binance API Key")
    binance_api_secret: str = Field(..., description="Binance API Secret")
    binance_testnet: bool = Field(default=True)

    # Simulation / Paper Trading
    simulation_mode: bool = Field(
        default=False,
        description="Ativa modo simulacao (paper trading) sem ordens reais na exchange",
    )
    simulation_initial_balance: Annotated[float, Field(ge=100)] = Field(
        default=10_000.0,
        description="Saldo inicial simulado em USDT para paper trading",
    )

    # Symbols, timeframes e leverage — triplets explícitos (SPEC_018)
    # Substitui SYMBOLS × TIMEFRAMES × LEVERAGE (produto cartesiano)
    # Formato: "SYMBOL:TIMEFRAME:LEVERAGE,..." ex: "BTCUSDT:15m:5,XPTUSDT:1h:3"
    symbol_timeframes: Annotated[list[SymbolConfig], NoDecode] = Field(
        default_factory=lambda: [
            SymbolConfig.from_triplet("BTCUSDT:15m:5"),
            SymbolConfig.from_triplet("ETHUSDT:15m:5"),
        ]
    )

    # Risk management
    risk_per_trade_pct: Annotated[float, Field(gt=0, le=5)] = 1.0
    risk_reward_ratio: Annotated[float, Field(ge=1.0)] = 2.0
    max_capital_allocation_pct: Annotated[float, Field(gt=0, le=100)] = 20.0
    max_open_positions: Annotated[int, Field(ge=1)] = 3

    # Commodities — gate de segurança: ativar apenas após backtest aprovado (INV-018-01)
    commodities_backtest_validated: bool = False

    # MongoDB
    mongodb_uri: str = Field(default="mongodb://mongo:27017")
    mongodb_database: str = Field(default="phicube")
    trade_history_retention_days: Annotated[int, Field(ge=90)] = 90

    # App
    log_level: str = Field(default="INFO")
    warmup_candles: Annotated[int, Field(ge=50, le=1000)] = 200

    # Telegram notifications (optional)
    telegram_token: str | None = Field(
        default=None,
        description="Telegram Bot Token para notificações (opcional)",
    )
    telegram_chat_id: str | None = Field(
        default=None,
        description="Telegram Chat ID para notificações (opcional)",
    )
    performance_report_interval_hours: Annotated[float, Field(ge=0)] = 24.0
    sl_missing_renotify_interval_minutes: Annotated[int, Field(ge=5)] = 15
    order_monitor_manual_close_confirm_cycles: Annotated[int, Field(ge=1)] = 3
    order_monitor_manual_close_require_dual_source: bool = True
    runtime_monitor_auto_sync: bool = False
    runtime_monitor_auto_sync_interval_seconds: Annotated[int, Field(ge=5)] = 30

    # Dashboard (API Key READ_ONLY — sem permissão de trade)
    dashboard_api_key: str = Field(..., description="Dashboard API Key (READ_ONLY)")
    dashboard_api_secret: str = Field(..., description="Dashboard API Secret (READ_ONLY)")
    dashboard_testnet_api_key: str | None = Field(
        default=None,
        description="Dashboard API Key da Binance Testnet (READ_ONLY)",
    )
    dashboard_testnet_api_secret: str | None = Field(
        default=None,
        description="Dashboard API Secret da Binance Testnet (READ_ONLY)",
    )
    dashboard_write_auth_required: bool = Field(
        default=False,
        description="Exige autenticacao para endpoints de escrita do dashboard",
    )
    dashboard_write_auth_token: str | None = Field(
        default=None,
        description="Token Bearer para endpoints de escrita quando auth estiver habilitada",
    )

    @field_validator("symbol_timeframes", mode="before")
    @classmethod
    def parse_symbol_timeframes_csv(cls, v: str | list) -> list[SymbolConfig]:
        if isinstance(v, str):
            return [SymbolConfig.from_triplet(t.strip()) for t in v.split(",") if t.strip()]
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper

    @model_validator(mode="before")
    @classmethod
    def apply_dashboard_testnet_alias(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        raw_binance_testnet = data.get("binance_testnet", True)
        is_testnet_enabled = raw_binance_testnet
        if isinstance(raw_binance_testnet, str):
            is_testnet_enabled = raw_binance_testnet.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }

        if is_testnet_enabled:
            testnet_api_key = data.get("dashboard_testnet_api_key")
            testnet_api_secret = data.get("dashboard_testnet_api_secret")

            if testnet_api_key:
                data["dashboard_api_key"] = testnet_api_key
            if testnet_api_secret:
                data["dashboard_api_secret"] = testnet_api_secret

        return data

    @model_validator(mode="after")
    def validate_commodities_gate(self) -> Settings:
        """INV-018-01: commodities bloqueadas sem backtest validado."""
        has_commodity = any(c.symbol in _COMMODITIES for c in self.symbol_timeframes)
        if has_commodity and not self.commodities_backtest_validated:
            raise ValueError(
                "Commodities detectadas em SYMBOL_TIMEFRAMES mas backtest não validado. "
                "Defina COMMODITIES_BACKTEST_VALIDATED=true após concluir backtest."
            )
        if self.dashboard_write_auth_required and not self.dashboard_write_auth_token:
            raise ValueError(
                "DASHBOARD_WRITE_AUTH_TOKEN obrigatorio quando "
                "DASHBOARD_WRITE_AUTH_REQUIRED=true."
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return cast(Any, Settings)()
