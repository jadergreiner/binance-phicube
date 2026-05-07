from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

SPEC_DIR = Path("docs/SDD/SPEC_023_FECHAMENTO_GAPS_PRD_MVP_OKR")
REQUIRED_SPEC_FILES = [
    "SPEC.md",
    "plan.md",
    "tasks.json",
    "tasks_status.json",
    "spec_status_update.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SPEC_023 artifacts and objective gates.")
    parser.add_argument("--mode", choices=["structure", "full"], default="full")
    parser.add_argument("--coverage-gate", default="reports/spec023_coverage_gate.json")
    parser.add_argument("--order-audit", default="reports/spec023_order_exec_audit.json")
    parser.add_argument("--stability-report", default="reports/spec023_runtime_stability.json")
    parser.add_argument(
        "--soak-evidence",
        default="docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/evidence/soak_evidence.json",
    )
    parser.add_argument("--output", default="reports/spec023_validation_report.json")
    return parser.parse_args()


def _load_json(path: Path, failures: list[str], *, label: str) -> dict | None:
    if not path.exists():
        failures.append(f"missing_file:{label}:{path.as_posix()}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"invalid_json:{label}:{exc}")
        return None


def _validate_spec_structure(failures: list[str]) -> None:
    for file_name in REQUIRED_SPEC_FILES:
        if not (SPEC_DIR / file_name).exists():
            failures.append(f"missing_spec_file:{file_name}")
    for file_name in ["tasks.json", "tasks_status.json"]:
        path = SPEC_DIR / file_name
        if not path.exists():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"invalid_spec_json:{file_name}:{exc}")


def _run_soak_validator(failures: list[str]) -> tuple[int | None, str]:
    proc = subprocess.run(
        [sys.executable, "scripts/spec_021/validate_soak_evidence.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        failures.append("soak_evidence_validation_failed")
    return proc.returncode, proc.stdout.strip()


def main() -> int:
    args = parse_args()
    failures: list[str] = []
    checks: dict[str, object] = {}

    _validate_spec_structure(failures)

    soak_validator_output = ""
    if args.mode == "full":
        coverage_payload = _load_json(Path(args.coverage_gate), failures, label="coverage_gate")
        if coverage_payload:
            checks["coverage_gate_status"] = coverage_payload.get("status")
            if coverage_payload.get("status") != "pass":
                failures.append("coverage_gate_not_pass")
            if float(coverage_payload.get("actual_percent", 0.0)) <= 80.0:
                failures.append("coverage_percent_not_strictly_above_80")

        order_payload = _load_json(Path(args.order_audit), failures, label="order_audit")
        if order_payload:
            checks["order_audit_status"] = order_payload.get("status")
            if order_payload.get("status") != "pass":
                failures.append("order_audit_not_pass")
            if int(order_payload.get("total_records", 0)) < 50:
                failures.append("order_audit_total_records_below_50")
            if float(order_payload.get("success_rate", 0.0)) != 100.0:
                failures.append("order_audit_success_rate_not_100")

        stability_payload = _load_json(
            Path(args.stability_report), failures, label="runtime_stability"
        )
        if stability_payload:
            checks["runtime_stability_status"] = stability_payload.get("status")
            if stability_payload.get("status") != "pass":
                failures.append("runtime_stability_not_pass")

        soak_payload = _load_json(Path(args.soak_evidence), failures, label="soak_evidence")
        if soak_payload:
            checks["soak_result"] = soak_payload.get("result")
            if soak_payload.get("result") != "approved":
                failures.append("soak_result_not_approved")
            if float(soak_payload.get("duration_hours", 0.0)) < 48.0:
                failures.append("soak_duration_below_48h")

        soak_validator_exit, soak_validator_output = _run_soak_validator(failures)
        checks["soak_validator_exit"] = soak_validator_exit

    result = {
        "status": "pass" if not failures else "fail",
        "mode": args.mode,
        "checked_at": datetime.now(UTC).isoformat(),
        "checks": checks,
        "failures": failures,
        "soak_validator_output": soak_validator_output,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
