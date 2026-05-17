from __future__ import annotations

import secrets
from dataclasses import dataclass
from enum import StrEnum
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
                f"Leverage inválida em triplet: {triplet!r}. Valor permitido: inteiro entre 1 e 20."
            )
        return cls(symbol=symbol.upper(), timeframe=timeframe, leverage=leverage)


class SizingMode(StrEnum):
    """Modo de position sizing — SPEC_029."""

    FIXED = "fixed"
    ATR = "atr"


@dataclass(frozen=True)
class TpLevel:
    """Nível de Take-Profit parcial."""

    qty_pct: float  # Percentual da posição (ex: 50.0 = 50%)
    price_distance_pct: float  # Distância do TP em % a partir do entry (ex: 2.0 = 2%)


class ExitStrategy(StrEnum):
    """Estratégia de saída — SPEC_030."""

    FIXED = "fixed"
    PARTIAL = "partial"
    TRAILING = "trailing"
    # PARTIAL_TRAILING = "partial+trailing"  # postergado


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

    # SPEC_029 — Position Sizing por ATR
    sizing_mode: SizingMode = SizingMode.FIXED
    risk_per_trade_usdt: Annotated[float, Field(gt=0)] = 5.0
    atr_period: Annotated[int, Field(ge=2, le=100)] = 14
    atr_multiplier: Annotated[float, Field(ge=0.5, le=10.0)] = 1.5
    min_position_usdt: Annotated[float, Field(ge=1.0)] = 10.0
    max_position_usdt: Annotated[float, Field(ge=1.0)] = 500.0
    atr_margin_risk_multiplier: Annotated[float, Field(gt=0.1, le=20.0)] = Field(
        default=10.0,
        description="Multiplicador do RISK_PER_TRADE_USDT para limitar margem máxima no modo ATR",
    )
    atr_multiplier_overrides: dict[str, float] = Field(
        default_factory=dict,
        description="Override de atr_multiplier por par. Ex: {'BTCUSDT': 2.0, 'BROCCOLI714': 3.0}",
    )

    # Exit strategy (SPEC_030)
    exit_strategy: ExitStrategy = ExitStrategy.FIXED
    tp_levels: list[dict[str, float]] = Field(
        default_factory=lambda: [
            {"qty_pct": 50.0, "price_distance_pct": 2.0},
            {"qty_pct": 50.0, "price_distance_pct": 4.0},
        ],
        description="Níveis de TP parcial: lista de {qty_pct, price_distance_pct}. "
        "Mínimo 1, máximo 3 níveis. Soma de qty_pct <= 100. "
        "Nota: `pct` é aceito como alias de `price_distance_pct` para compatibilidade.",
    )
    exit_strategy_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Override de exit_strategy por par. Ex: {'BTCUSDT': 'partial'}",
    )

    # Trailing Stop (SPEC_030 V2)
    trailing_activation_pct: Annotated[float, Field(ge=0.1, le=20.0)] = Field(
        default=1.0,
        description="Percentual de lucro para ativar o trailing stop",
    )
    trailing_callback_rate: Annotated[float, Field(ge=0.1, le=10.0)] = Field(
        default=0.5,
        description="Callback rate do trailing stop em %% (0.1-10.0)",
    )

    # SPEC_043 — Slippage Protection, priceProtect e Circuit Breaker
    max_position_pct: Annotated[float, Field(ge=0, le=100)] = Field(
        default=0.0,
        description="Limite máximo da posição como %% do saldo "
        "(0=desabilitado, usa MAX_POSITION_USDT)",
    )
    consecutive_loss_threshold: Annotated[int, Field(ge=1, le=10)] = Field(
        default=3,
        description="Nº de perdas consecutivas para ativar circuit breaker do par",
    )
    portfolio_loss_threshold: Annotated[int, Field(ge=1, le=10)] = Field(
        default=2,
        description="Nº de perdas em pares diferentes para ativar circuit breaker de portfólio",
    )
    slippage_tolerance_multiplier: Annotated[float, Field(ge=1.0)] = Field(
        default=1.10,
        description="Multiplicador de tolerância de slippage (normal)",
    )
    slippage_tolerance_reduced: Annotated[float, Field(ge=1.0)] = Field(
        default=1.05,
        description="Multiplicador de tolerância de slippage (com CB ativo)",
    )
    cb_risk_reduction_factor: Annotated[float, Field(gt=0, le=1.0)] = Field(
        default=0.5,
        description="Fator de redução de risco do circuit breaker pair-level",
    )
    portfolio_risk_reduction_factor: Annotated[float, Field(gt=0, le=1.0)] = Field(
        default=0.75,
        description="Fator de redução de risco do circuit breaker de portfólio",
    )
    recovery_wins_needed: Annotated[int, Field(ge=1, le=10)] = Field(
        default=1,
        description="Nº de vitórias consecutivas para reset do circuit breaker",
    )
    slippage_validation_enabled: bool = Field(
        default=False,
        description="Feature flag: ativa validação de slippage no RiskManager",
    )
    circuit_breaker_enabled: bool = Field(
        default=False,
        description="Feature flag: ativa circuit breaker de perdas consecutivas",
    )
    predictive_breaker_enabled: bool = Field(
        default=False,
        description="Feature flag: ativa circuit breaker preditivo pré-trade",
    )
    predictive_breaker_percentile: Annotated[float, Field(gt=0.0, lt=1.0)] = Field(
        default=0.85,
        description="Percentil para gatilho do ATR ratio no breaker preditivo (0-1)",
    )
    predictive_breaker_window: Annotated[int, Field(ge=20, le=500)] = Field(
        default=100,
        description="Janela histórica de candles usada no cálculo do percentil preditivo",
    )
    predictive_breaker_tiers: list[str] = Field(
        default_factory=lambda: ["low"],
        description="Tiers de liquidez elegíveis ao breaker preditivo",
    )

    # Commodities — gate de segurança: ativar apenas após backtest aprovado (INV-018-01)
    commodities_backtest_validated: bool = False

    # MongoDB
    mongodb_uri: str = Field(default="mongodb://mongo:27017")
    mongodb_database: str = Field(default="phicube")
    trade_history_retention_days: Annotated[int, Field(ge=90)] = 90
    circuit_breaker_mongo_recovery_timeout_secs: Annotated[int, Field(ge=10)] = 60
    circuit_breaker_binance_recovery_timeout_secs: Annotated[int, Field(ge=10)] = 30

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

    # MCP-PoS (Point-of-Sale) — Customer table config (spec-driven)
    mcp_pos_customer_fields: str = Field(
        default="name,email,phone,document,status,notes",
        description="Campos do Cliente MCP-PoS separados por virgula (spec-driven)",
    )

    # MCP Serena execution context
    mcp_serena_context: dict[str, str | None] = Field(
        default_factory=lambda: {
            "version": "1.0",
            "spec_path": "docs/SDD/SPEC.md",
            "module": "MCP-PoS Customer",
            "execution_status": "active",
        },
        description="Contexto de execucao do fluxo MCP Serena",
    )

    # SPEC_033 — Strategy Plugin Architecture
    symbol_strategy_map: dict[str, str] = Field(
        default_factory=dict,
        description="Mapeamento símbolo → nome do plugin. Ex: BTCUSDT:williams,ETHUSDT:williams",
    )
    default_strategy: str = Field(
        default="williams",
        description="Plugin padrão para símbolos não mapeados em SYMBOL_STRATEGY_MAP",
    )
    plugin_timeout: Annotated[float, Field(ge=1.0, le=120.0)] = Field(
        default=30.0,
        description="Timeout em segundos para evaluate() de plugins de estratégia",
    )
    ml_support_enabled: bool = Field(
        default=False,
        description="Feature flag global da camada ML auxiliar operacional",
    )
    ml_support_shadow_mode: bool = Field(
        default=True,
        description="Executa ML apenas para diagnóstico, sem impacto em ordens",
    )
    ml_support_symbol_timeframes: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        description="Escopo canário de ML no formato SYMBOL:TIMEFRAME",
    )

    # SPEC_034 — Pipeline Pattern para Tick
    tick_pipeline_enabled: bool = Field(
        default=False,
        description="Feature flag: ativa pipeline de middlewares para processamento de ticks",
    )

    # SPEC_032 — Prometheus Metrics
    prometheus_enabled: bool = Field(
        default=True,
        description="Ativa endpoint /metrics no formato Prometheus",
    )
    prometheus_port: Annotated[int, Field(ge=1024, le=65535)] = Field(
        default=8000,
        description="Porta para o servidor de métricas Prometheus",
    )
    prometheus_bind_host: str = Field(
        default="127.0.0.1",
        description="Interface para bind do servidor de métricas (segurança: localhost padrão)",
    )

    # Backtest (SPEC_028) — Slippage por tier de liquidez
    backtest_slippage_by_liq: dict[str, float] = Field(
        default_factory=lambda: {
            "high": 0.0003,
            "medium": 0.0008,
            "low": 0.0015,
        },
        description="Slippage percentual por tier de liquidez (high/medium/low)",
    )
    backtest_slippage_liq_map: dict[str, str] = Field(
        default_factory=lambda: {
            "BTCUSDT": "high",
            "ETHUSDT": "high",
            "SOLUSDT": "medium",
            "LINKUSDT": "medium",
            "AVAXUSDT": "medium",
            "DOTUSDT": "medium",
            "MATICUSDT": "medium",
            "ATOMUSDT": "medium",
            "UNIUSDT": "medium",
            "LTCUSDT": "medium",
            "BCHUSDT": "medium",
            "ETCUSDT": "medium",
            "FILUSDT": "medium",
            "NEARUSDT": "medium",
            "APTUSDT": "medium",
            "ARBUSDT": "medium",
            "OPUSDT": "medium",
            "INJUSDT": "medium",
            "RUNEUSDT": "medium",
            "AAVEUSDT": "medium",
            "MKRUSDT": "medium",
            "ADAUSDT": "low",
            "ALGOUSDT": "low",
            "XRPUSDT": "low",
            "DOGEUSDT": "low",
            "TRXUSDT": "low",
            "VETUSDT": "low",
            "ICPUSDT": "low",
            "XLMUSDT": "low",
            "HBARUSDT": "low",
            "EGLDUSDT": "low",
            "SANDUSDT": "low",
            "MANAUSDT": "low",
            "THETAUSDT": "low",
            "FTMUSDT": "low",
        },
        description="Mapeamento símbolo -> tier de liquidez (default: medium para não-listados)",
    )
    backtest_maker_fee: float = Field(
        default=0.0002,
        description="Taxa maker (padrão Binance VIP 0: 0.02%%)",
    )
    backtest_taker_fee: float = Field(
        default=0.0005,
        description="Taxa taker (padrão Binance VIP 0: 0.05%%)",
    )

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

    # SPEC_036 — OAuth Google Authentication
    google_client_id: str | None = Field(
        default=None,
        description="Google OAuth Client ID",
    )
    google_client_secret: str | None = Field(
        default=None,
        description="Google OAuth Client Secret",
    )
    google_redirect_uri: str | None = Field(
        default=None,
        description="Google OAuth Redirect URI",
    )
    auth_post_login_redirect_uri: str = Field(
        default="http://localhost:3000/auth/callback",
        description="URL da SPA para receber o JWT após o login OAuth",
    )
    auth_allowed_emails: list[str] = Field(
        default_factory=list,
        description="Lista de emails autorizados a acessar o dashboard",
    )
    auth_dev_bypass: bool = Field(
        default=False,
        description="Ativa modo dev bypass (login simples sem OAuth)",
    )
    auth_fallback_user: str = Field(
        default="",
        description="Usuário fallback para recovery",
    )
    auth_fallback_password_hash: str = Field(
        default="",
        description="Bcrypt hash da senha fallback",
    )
    jwt_secret: str | None = Field(
        default=None,
        description="JWT Secret para autenticação",
    )
    jwt_expiry_hours: int = Field(
        default=24,
        description="Tempo de expiração do JWT em horas",
    )

    @field_validator("symbol_timeframes", mode="before")
    @classmethod
    def parse_symbol_timeframes_csv(cls, v: str | list) -> list[SymbolConfig]:
        if isinstance(v, str):
            return [SymbolConfig.from_triplet(t.strip()) for t in v.split(",") if t.strip()]
        return v

    @field_validator("symbol_strategy_map", mode="before")
    @classmethod
    def parse_symbol_strategy_map(cls, v: str | dict) -> dict[str, str]:
        if isinstance(v, str):
            result: dict[str, str] = {}
            for pair in v.split(","):
                pair = pair.strip()
                if ":" in pair:
                    sym, strat = pair.split(":", 1)
                    result[sym.strip().upper()] = strat.strip()
            return result
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper

    @field_validator("ml_support_symbol_timeframes", mode="before")
    @classmethod
    def parse_ml_support_symbol_timeframes(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            values = [item.strip() for item in v.split(",") if item.strip()]
        else:
            values = [str(item).strip() for item in v if str(item).strip()]

        normalized: list[str] = []
        for pair in values:
            if ":" not in pair:
                raise ValueError(
                    "ml_support_symbol_timeframes deve usar formato SYMBOL:TIMEFRAME"
                )
            symbol, timeframe = pair.split(":", 1)
            normalized.append(f"{symbol.strip().upper()}:{timeframe.strip().lower()}")
        return normalized

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

    def get_atr_multiplier(self, symbol: str) -> float:
        """Retorna atr_multiplier com suporte a override por par.

        Se existir override em atr_multiplier_overrides para o símbolo,
        usa o valor dele. Caso contrário, usa o atr_multiplier global.
        """
        override_val = self.atr_multiplier_overrides.get(symbol.upper())
        if override_val is not None:
            return float(override_val)
        return self.atr_multiplier

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
                "DASHBOARD_WRITE_AUTH_TOKEN obrigatorio quando DASHBOARD_WRITE_AUTH_REQUIRED=true."
            )
        return self

    @model_validator(mode="after")
    def ensure_jwt_secret(self) -> Settings:
        """Garante segredo JWT mesmo quando o .env não define um valor explícito."""
        if not self.jwt_secret:
            self.jwt_secret = secrets.token_urlsafe(48)
        return self

    @model_validator(mode="after")
    def validate_exit_strategy(self) -> Settings:
        """D-006: Valida configuração de saída dinâmica. Erro fatal no startup."""
        # Adapter Pattern: normalizar `pct` (alias) → `price_distance_pct` (canonical)
        # para que downstream (OrderManager) sempre encontre o campo canônico.
        levels = self.tp_levels
        if not isinstance(levels, list):
            raise ValueError(f"tp_levels deve ser uma lista, recebeu {type(levels).__name__}")
        for level in levels:
            if "pct" in level and "price_distance_pct" not in level:
                level["price_distance_pct"] = level.pop("pct")

        if not (1 <= len(levels) <= 3):
            raise ValueError(f"tp_levels deve ter entre 1 e 3 níveis, mas tem {len(levels)}")

        total_qty = 0.0
        for i, level in enumerate(levels):
            qty = level.get("qty_pct", 0)
            price_dist = level.get("price_distance_pct", 0)
            if not isinstance(qty, (int, float)) or qty <= 0:
                raise ValueError(f"tp_levels[{i}].qty_pct deve ser > 0, recebeu {qty}")
            if not isinstance(price_dist, (int, float)) or price_dist <= 0:
                raise ValueError(
                    f"tp_levels[{i}].price_distance_pct deve ser > 0, recebeu {price_dist}"
                )
            total_qty += qty

        if total_qty > 100.0:
            raise ValueError(f"Soma de tp_levels qty_pct é {total_qty}% — deve ser <= 100%")

        # Validar exit_strategy
        if self.exit_strategy == ExitStrategy.TRAILING:
            if self.trailing_activation_pct <= self.trailing_callback_rate:
                raise ValueError(
                    f"trailing_activation_pct ({self.trailing_activation_pct}) deve ser maior "
                    f"que trailing_callback_rate ({self.trailing_callback_rate})"
                )

        # Validar exit_strategy_overrides
        valid_strategies = {"fixed", "partial", "trailing"}
        for symbol, strategy in (self.exit_strategy_overrides or {}).items():
            if strategy not in valid_strategies:
                raise ValueError(
                    f"exit_strategy_overrides[{symbol!r}] = {strategy!r} inválido. "
                    f"Valores permitidos: {valid_strategies}"
                )

        return self

    def log_exit_strategy_config(self) -> None:
        """Loga configuração de saída no startup."""
        from src.monitoring.logger import get_logger

        log = get_logger(__name__)
        log.info(
            "exit_strategy_configured",
            strategy=self.exit_strategy.value,
            tp_levels=self.tp_levels,
            overrides=self.exit_strategy_overrides,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return cast(Any, Settings)()
