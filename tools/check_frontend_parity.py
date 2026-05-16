"""Smoke de release do frontend canônico (:8080)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

import requests

DEFAULT_MARKERS = (
    'id="sort-key"',
    'id="sort-dir"',
    'id="save-view-btn"',
    'id="top-symbols-profitable"',
    'id="top-symbols-losing"',
    'id="best-trade"',
    'id="worst-trade"',
)


def _fetch(url: str) -> str:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text


def _missing_markers(content: str, markers: Iterable[str]) -> list[str]:
    return [marker for marker in markers if marker not in content]


def _probe_assertiveness(base_url: str, timeframe: str) -> tuple[bool, str]:
    end = datetime.now(UTC).replace(microsecond=0)
    start = end - timedelta(hours=24)
    response = requests.get(
        base_url.rstrip("/") + "/performance/assertiveness",
        params={
            "period": "custom",
            "timeframe": timeframe,
            "start": start.isoformat().replace("+00:00", "Z"),
            "end": end.isoformat().replace("+00:00", "Z"),
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    has_summary = isinstance(payload.get("summary"), dict)
    has_ranking = isinstance(payload.get("ranking"), list)
    if not has_summary or not has_ranking:
        return False, "payload sem summary/ranking"
    return True, f"ranking_count={len(payload.get('ranking', []))}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Executa smoke único de release para o frontend canônico em :8080.")
    )
    parser.add_argument("--canonical-url", default="http://127.0.0.1:8080")
    parser.add_argument("--timeframe", default="15m")
    parser.add_argument("--skip-assertiveness", action="store_true")
    args = parser.parse_args()

    canonical_html = _fetch(args.canonical_url.rstrip("/") + "/")
    missing_in_canonical = _missing_markers(canonical_html, DEFAULT_MARKERS)

    if missing_in_canonical:
        print("ERRO: frontend canônico está sem marcadores críticos:")
        for marker in missing_in_canonical:
            print(f" - {marker}")
        return 2

    health_response = requests.get(args.canonical_url.rstrip("/") + "/health", timeout=10)
    health_response.raise_for_status()

    if not args.skip_assertiveness:
        ok, details = _probe_assertiveness(args.canonical_url, args.timeframe)
        if not ok:
            print(f"ERRO: assertiveness inválido: {details}")
            return 3
        print(f"OK: /performance/assertiveness validado ({details})")

    print("OK: smoke do frontend canônico concluído em :8080.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
