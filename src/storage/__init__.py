"""
Camada de persistência — MongoDB e storage local.

Componentes:
    MongoRepository — persistência em MongoDB (trades, signals, audit)
    PendingTradesJournal — persistência local .jsonl para trades não-persistidos
    ResilientMongoRepository — Facade com CB + retry + journal para resiliência
"""

from src.storage.pending_trades_journal import PendingTradesJournal
from src.storage.repository import MongoRepository
from src.storage.resilient_repository import ResilientMongoRepository

__all__ = [
    "MongoRepository",
    "PendingTradesJournal",
    "ResilientMongoRepository",
]
