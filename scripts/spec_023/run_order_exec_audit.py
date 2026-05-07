from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pymongo import DESCENDING
from pymongo.mongo_client import MongoClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit batch execution results from MongoDB trades."
    )
    parser.add_argument("--uri", default=os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    parser.add_argument("--database", default=os.getenv("MONGODB_DATABASE", "phicube"))
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--output", default="reports/spec023_order_exec_audit.json")
    return parser.parse_args()


def classify_failure(trade: dict) -> str:
    if trade.get("status") == "FAILED":
        return "status_failed"
    if not trade.get("sl_order_id"):
        return "missing_sl_order"
    if not trade.get("tp_order_id"):
        return "missing_tp_order"
    return "unknown_failure"


def is_successful_execution(trade: dict) -> bool:
    return (
        trade.get("status") in {"OPEN", "CLOSED_TP", "CLOSED_SL", "CLOSED_MANUAL"}
        and bool(trade.get("sl_order_id"))
        and bool(trade.get("tp_order_id"))
    )


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        client = MongoClient(args.uri, serverSelectionTimeoutMS=5000)
        try:
            trades = list(
                client[args.database]["trades"]
                .find({}, {"_id": 0})
                .sort("opened_at", DESCENDING)
                .limit(args.batch_size)
            )
        finally:
            client.close()
    except Exception as exc:  # noqa: BLE001 - operational script should emit deterministic artifact
        output = {
            "generated_at": datetime.now(UTC).isoformat(),
            "batch_size_requested": args.batch_size,
            "total_records": 0,
            "success_count": 0,
            "failure_count": 0,
            "success_rate": 0.0,
            "failure_causes": {"mongo_query_failed": 1},
            "status": "fail",
            "error": type(exc).__name__,
        }
        output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(json.dumps(output, indent=2))
        return 1

    success = 0
    failures = 0
    causes = Counter()

    for trade in trades:
        if is_successful_execution(trade):
            success += 1
        else:
            failures += 1
            causes[classify_failure(trade)] += 1

    total = len(trades)
    success_rate = (success / total * 100.0) if total else 0.0

    output = {
        "generated_at": datetime.now(UTC).isoformat(),
        "batch_size_requested": args.batch_size,
        "total_records": total,
        "success_count": success,
        "failure_count": failures,
        "success_rate": round(success_rate, 4),
        "failure_causes": dict(causes),
        "status": "pass" if total >= args.batch_size and success_rate == 100.0 else "fail",
    }

    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))

    return 0 if output["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
