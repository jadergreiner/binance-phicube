"""
Camada de persistência — MongoDB e storage local.

Componentes:
    MongoRepository — persistência em MongoDB (trades, signals, audit)
    PendingTradesJournal — persistência local .jsonl para trades não-persistidos
"""

from src.storage.pending_trades_journal import PendingTradesJournal
from src.storage.repository import MongoRepository

__all__ = [
    "MongoRepository",
    "PendingTradesJournal",
]
