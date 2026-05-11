"""Entidades e contexto de execução do módulo MCP-PoS (Point-of-Sale)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class Customer:
    id: str | None = None
    name: str = ""
    email: str | None = None
    phone: str | None = None
    document: str | None = None
    status: str = "active"
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "document": self.document,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at or datetime.now(UTC),
            "updated_at": self.updated_at or datetime.now(UTC),
        }
        return d


mcp_serena_context: dict[str, str | None] = {
    "version": "1.0",
    "spec_path": "docs/SDD/SPEC.md",
    "module": "MCP-PoS Customer",
    "execution_status": "active",
}
