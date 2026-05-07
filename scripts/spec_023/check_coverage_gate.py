from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate strict coverage gate for SPEC_023.")
    parser.add_argument("--coverage", default="reports/coverage.json")
    parser.add_argument("--output", default="reports/spec023_coverage_gate.json")
    parser.add_argument("--threshold", type=float, default=80.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    coverage_path = Path(args.coverage)
    output_path = Path(args.output)

    if not coverage_path.exists():
        output = {
            "status": "fail",
            "reason": "coverage_file_missing",
            "coverage_path": coverage_path.as_posix(),
            "threshold": args.threshold,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(json.dumps(output, indent=2))
        return 1

    payload = json.loads(coverage_path.read_text(encoding="utf-8"))
    totals = payload.get("totals", {})
    percent = float(totals.get("percent_covered", 0.0))

    output = {
        "status": "pass" if percent > args.threshold else "fail",
        "threshold": args.threshold,
        "actual_percent": percent,
        "covered_lines": totals.get("covered_lines"),
        "num_statements": totals.get("num_statements"),
        "coverage_path": coverage_path.as_posix(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0 if output["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
