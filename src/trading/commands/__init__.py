"""Command Pattern para operações de ordem.

Encapsula operações de ordem (entry, SL, TP) como objetos Command
com execute() e undo(), permitindo rollback automático em caso de falha.
"""

from src.trading.commands.base import Command
from src.trading.commands.market_order import CreateMarketOrderCommand
from src.trading.commands.pipeline import OrderPipeline
from src.trading.commands.stop_loss import CreateStopLossCommand
from src.trading.commands.take_profit import CreateTakeProfitCommand

__all__ = [
    "Command",
    "CreateMarketOrderCommand",
    "CreateStopLossCommand",
    "CreateTakeProfitCommand",
    "OrderPipeline",
]
