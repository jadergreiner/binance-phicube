from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

# Definindo tipos literais para maior segurança
OrderStatus = Literal["FILLED", "PARTIALLY_FILLED", "CANCELED"]
Direction = Literal["BUY", "SELL"]


@dataclass
class OrderExecutedEvent:
    # Metadados obrigatórios de rastreabilidade
    order_id: str  # ID da ordem na Binance/Exchange
    internal_trade_id: str  # ID interno gerado pelo nosso sistema
    user_id: str

    # Dados do Trade
    asset_symbol: str  # Ex: BTCUSDT
    direction: Direction  # BUY ou SELL
    side: Literal["LONG", "SHORT"]  # Posição
    executed_quantity: float
    avg_price: float  # Preço médio de execução (Crucial)

    # Metadados de Auditoria
    status: OrderStatus
    timestamp: datetime = field(default_factory=datetime.utcnow)
    exchange_details: dict  # Para guardar dados brutos do ccxt/Binance se necessário


@dataclass
class SystemFailureEvent:
    source_module: str  # Ex: "OrderManager", "DatabaseAdapter"
    failure_type: str  # Ex: "CONNECTION_ERROR", "SERIALIZATION_ERROR"
    error_details: str  # A mensagem de erro capturada (string)
    traceback_snippet: str  # Um trecho do traceback para contexto rápido
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SLLimitBreachEvent:
    order_id: str
    asset_symbol: str
    position_side: Literal["LONG", "SHORT"]
    entry_price: float
    set_sl_price: float
    current_market_price: float
    loss_potential: float  # Cálculo simples para o alerta: (Entry - Market) * Quantity
    timestamp: datetime = field(default_factory=datetime.utcnow)
