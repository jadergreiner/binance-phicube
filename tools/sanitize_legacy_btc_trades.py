"""Saneia trades legados inválidos de BTCUSDT para proteger métricas RF-11.

Critério alvo:
- symbol == BTCUSDT
- trade_id is null
- quantity is null
- side is null
- entry_price fora de faixa configurada

Modo padrão: dry-run (não altera dados).
Use --apply para efetivar.
"""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pymongo import MongoClient


def _load_env_file() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _entry_out_of_range_filter(min_entry: float, max_entry: float) -> dict[str, Any]:
    return {
        "$or": [
            {"entry_price": {"$lt": min_entry}},
            {"entry_price": {"$gt": max_entry}},
            {"entry_price": None},
        ]
    }


def _build_strict_filter(symbol: str, min_entry: float, max_entry: float) -> dict[str, Any]:
    return {
        "symbol": symbol.upper(),
        "trade_id": None,
        "quantity": None,
        "side": None,
        **_entry_out_of_range_filter(min_entry, max_entry),
        "excluded_from_metrics": {"$ne": True},
    }


def _build_fallback_filter(symbol: str, min_entry: float, max_entry: float) -> dict[str, Any]:
    return {
        "symbol": symbol.upper(),
        "status": {"$in": ["CLOSED_TP", "CLOSED_SL", "CLOSED_MANUAL"]},
        **_entry_out_of_range_filter(min_entry, max_entry),
        "excluded_from_metrics": {"$ne": True},
    }


def _print_sample(rows: list[dict[str, Any]]) -> None:
    for idx, row in enumerate(rows[:10], start=1):
        print(
            {
                "n": idx,
                "_id": str(row.get("_id")),
                "symbol": row.get("symbol"),
                "entry_price": row.get("entry_price"),
                "exit_price": row.get("exit_price"),
                "pnl_usdt": row.get("pnl_usdt"),
                "status": row.get("status"),
                "opened_at": str(row.get("opened_at")),
                "closed_at": str(row.get("closed_at")),
            }
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Saneia trades legados inválidos de BTCUSDT com backup e marcação de exclusão."
    )
    parser.add_argument("--apply", action="store_true", help="Efetiva alterações no banco.")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--min-entry", type=float, default=1_000.0)
    parser.add_argument("--max-entry", type=float, default=200_000.0)
    parser.add_argument("--mongo-uri", default=None)
    parser.add_argument("--mongo-db", default=None)
    parser.add_argument("--strict-only", action="store_true")
    args = parser.parse_args()

    _load_env_file()
    mongo_uri = args.mongo_uri or os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db = args.mongo_db or os.getenv("MONGO_DATABASE", "phicube")

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10_000)
    db = client[mongo_db]
    trades = db["trades"]
    backups = db["trades_sanitization_backups"]

    strict_filter = _build_strict_filter(args.symbol, args.min_entry, args.max_entry)
    matches = list(trades.find(strict_filter))
    mode = "strict"
    if not matches and not args.strict_only:
        fallback_filter = _build_fallback_filter(args.symbol, args.min_entry, args.max_entry)
        matches = list(trades.find(fallback_filter))
        mode = "fallback_entry_out_of_range"

    total = len(matches)
    pnl_total = round(sum(float(row.get("pnl_usdt") or 0.0) for row in matches), 4)
    print(f"mongo_uri={mongo_uri}")
    print(f"mongo_db={mongo_db}")
    print(f"symbol={args.symbol.upper()} mode={mode} matches={total} pnl_sum={pnl_total}")
    _print_sample(matches)

    if not args.apply:
        print("dry_run=true (nenhuma alteração aplicada)")
        return 0

    if not matches:
        print("apply=true sem matches; nada a alterar")
        return 0

    batch_id = (
        f"btc-legacy-sanitize-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    )
    now = datetime.now(UTC)

    backup_docs = [
        {
            "batch_id": batch_id,
            "reason": "legacy_btc_invalid_contract",
            "mode": mode,
            "captured_at": now,
            "original_id": row.get("_id"),
            "document": row,
        }
        for row in matches
    ]
    backups.insert_many(backup_docs, ordered=True)

    ids = [row["_id"] for row in matches if row.get("_id") is not None]
    result = trades.update_many(
        {"_id": {"$in": ids}},
        {
            "$set": {
                "excluded_from_metrics": True,
                "excluded_from_metrics_reason": f"legacy_btc_invalid_contract:{mode}",
                "excluded_from_metrics_at": now,
                "excluded_from_metrics_batch_id": batch_id,
            }
        },
    )
    print(
        "apply=true",
        {
            "batch_id": batch_id,
            "backup_inserted": len(backup_docs),
            "updated_count": result.modified_count,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
