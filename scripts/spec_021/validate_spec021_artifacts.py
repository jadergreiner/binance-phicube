from __future__ import annotations

import json
from pathlib import Path


SPEC_DIR = Path("docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA")
REQUIRED_FILES = [
    "SPEC.md",
    "plan.md",
    "tasks.json",
    "tasks_status.json",
    "spec_status_update.md",
    "soak_protocol.md",
    "soak_evidence.template.json",
    "compliance_matrix.md",
    "quality_gate.md",
    "hardening_checklist.md",
    "traceability_report.md",
]


def main() -> int:
    failures: list[str] = []
    for file_name in REQUIRED_FILES:
        if not (SPEC_DIR / file_name).exists():
            failures.append(f"missing required file: {file_name}")

    for json_file in ["tasks.json", "tasks_status.json", "soak_evidence.template.json"]:
        path = SPEC_DIR / json_file
        if not path.exists():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{json_file} invalid json: {exc}")

    if failures:
        print(json.dumps({"status": "fail", "failures": failures}, indent=2))
        return 1

    print(json.dumps({"status": "pass", "checked_files": REQUIRED_FILES}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
