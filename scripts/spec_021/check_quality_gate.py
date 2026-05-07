from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


THRESHOLDS = {
    "src/strategy/indicators.py": 90.0,
    "src/strategy/signal_engine.py": 85.0,
    "src/trading/risk_manager.py": 80.0,
    "src/trading/order_manager.py": 75.0,
    "src/storage/repository.py": 75.0,
}


def run_pytest_coverage(coverage_path: Path) -> int:
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=src",
        "--cov-report=term-missing",
        f"--cov-report=json:{coverage_path.as_posix()}",
    ]
    return subprocess.call(cmd)


def load_actual_coverage(coverage_path: Path) -> dict[str, float]:
    payload = json.loads(coverage_path.read_text(encoding="utf-8"))
    files = payload.get("files", {})
    actual: dict[str, float] = {}
    normalized_thresholds = {p.replace("\\", "/"): p for p in THRESHOLDS}
    for file_path, meta in files.items():
        normalized = file_path.replace("\\", "/")
        if normalized in normalized_thresholds:
            canonical = normalized_thresholds[normalized]
            actual[canonical] = float(meta["summary"]["percent_covered"])
    return actual


def evaluate(actual: dict[str, float]) -> tuple[str, list[str]]:
    failures: list[str] = []
    for file_path, threshold in THRESHOLDS.items():
        value = actual.get(file_path)
        if value is None:
            failures.append(f"missing coverage entry: {file_path}")
            continue
        if value < threshold:
            failures.append(f"{file_path} below threshold: {value:.2f}% < {threshold:.2f}%")
    return ("pass" if not failures else "fail", failures)


def main() -> int:
    reports_dir = Path("reports")
    coverage_file = reports_dir / "coverage.json"
    output_file = reports_dir / "spec021_quality_gate.json"

    pytest_exit = run_pytest_coverage(coverage_file)
    if pytest_exit != 0:
        result = {
            "status": "fail",
            "thresholds": THRESHOLDS,
            "actual": {},
            "failures": [f"pytest failed with exit code {pytest_exit}"],
        }
        output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 1

    if not coverage_file.exists():
        result = {
            "status": "fail",
            "thresholds": THRESHOLDS,
            "actual": {},
            "failures": ["coverage report file not generated"],
        }
        output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 1

    actual = load_actual_coverage(coverage_file)
    status, failures = evaluate(actual)

    result = {
        "status": status,
        "thresholds": THRESHOLDS,
        "actual": actual,
        "failures": failures,
    }
    output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
