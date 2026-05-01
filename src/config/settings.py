from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Binance
    binance_api_key: str = Field(..., description="Binance API Key")
    binance_api_secret: str = Field(..., description="Binance API Secret")
    binance_testnet: bool = Field(default=True)

    # Symbols and timeframes
    symbols: list[str] = Field(default=["BTCUSDT"])
    timeframes: list[str] = Field(default=["15m"])

    # Risk management
    risk_per_trade_pct: Annotated[float, Field(gt=0, le=5)] = 1.0
    risk_reward_ratio: Annotated[float, Field(ge=1.0)] = 2.0
    leverage: Annotated[int, Field(ge=1, le=125)] = 5
    max_capital_allocation_pct: Annotated[float, Field(gt=0, le=100)] = 30.0
    max_open_positions: Annotated[int, Field(ge=1)] = 3

    # MongoDB
    mongodb_uri: str = Field(default="mongodb://mongo:27017")
    mongodb_database: str = Field(default="phicube")

    # App
    log_level: str = Field(default="INFO")
    warmup_candles: Annotated[int, Field(ge=50, le=1000)] = 200

    @field_validator("symbols", "timeframes", mode="before")
    @classmethod
    def parse_csv(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [item.strip().upper() for item in v.split(",") if item.strip()]
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper

    # Dashboard (API Key READ_ONLY — sem permissão de trade)
    dashboard_api_key: str = Field(..., description="Dashboard API Key (READ_ONLY)")
    dashboard_api_secret: str = Field(..., description="Dashboard API Secret (READ_ONLY)")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
