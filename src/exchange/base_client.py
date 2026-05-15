from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class TradingClient(ABC):
    """Contrato abstrato para interação com exchanges de futuros.

    Precondição: `connect()` deve ser executado antes de operações de mercado/ordens.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Conecta à exchange e prepara recursos necessários."""

    @abstractmethod
    async def close(self) -> None:
        """Encerra conexão com a exchange e libera recursos."""

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        since: int | None = None,
    ) -> pd.DataFrame:
        """Retorna candles OHLCV em DataFrame."""

    @abstractmethod
    async def fetch_ohlcv_with_retry(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        retries: int | None = None,
        base_delay: float | None = None,
    ) -> pd.DataFrame:
        """Retorna OHLCV com política de retry."""

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        """Retorna ticker atual do símbolo."""

    @abstractmethod
    async def fetch_usdt_balance(self) -> float:
        """Retorna saldo disponível em USDT."""

    @abstractmethod
    async def fetch_balance(self) -> dict[str, Any]:
        """Retorna saldo completo da conta."""

    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> None:
        """Configura alavancagem para o símbolo informado."""

    @abstractmethod
    async def set_margin_mode(self, symbol: str, mode: str = "isolated") -> None:
        """Configura modo de margem para o símbolo informado."""

    @abstractmethod
    async def create_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Cria ordem de mercado e retorna payload da exchange."""

    @abstractmethod
    async def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
    ) -> dict[str, Any]:
        """Cria ordem de stop loss (STOP_MARKET)."""

    @abstractmethod
    async def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
    ) -> dict[str, Any]:
        """Cria ordem de take profit (TAKE_PROFIT_MARKET)."""

    @abstractmethod
    async def create_trailing_stop_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        activation_price: float,
        callback_rate: float,
    ) -> dict[str, Any]:
        """Cria ordem trailing stop (TRAILING_STOP_MARKET)."""

    @abstractmethod
    async def cancel_all_orders(self, symbol: str) -> None:
        """Cancela todas as ordens abertas do símbolo."""

    @abstractmethod
    async def fetch_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        """Retorna ordens abertas do símbolo."""

    @abstractmethod
    async def fetch_order(self, order_id: str, symbol: str) -> dict[str, Any]:
        """Retorna detalhes de uma ordem pelo ID."""

    @abstractmethod
    async def fetch_open_positions(self) -> list[dict[str, Any]]:
        """Retorna posições abertas."""

    @abstractmethod
    async def fetch_position_risk(
        self,
        *,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retorna risco/estado de posições."""

    async def validate_market_liquidity(
        self,
        symbol: str,
        min_volume: float = 500_000.0,
        min_oi: float = 200_000.0,
    ) -> None:
        """Valida liquidez do mercado.

        Implementação padrão: no-op compatível.
        """
        return None

    async def fetch_quantity_precision_map(self, symbols: list[str]) -> dict[str, int]:
        """Retorna mapa de precisão por símbolo.

        Implementação padrão: dicionário vazio compatível.
        """
        return {}

    @abstractmethod
    def get_quantity_precision(self, symbol: str) -> int:
        """Retorna casas decimais de quantidade para o símbolo."""

    @abstractmethod
    def round_quantity(self, symbol: str, qty: float) -> float:
        """Arredonda quantidade para o step/tick da exchange."""

    @abstractmethod
    def round_price(self, symbol: str, price: float) -> float:
        """Arredonda preço para o tick da exchange."""
