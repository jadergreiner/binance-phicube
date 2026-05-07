from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    evidence_path = Path(
        "docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/evidence/soak_evidence.json"
    )
    if not evidence_path.exists():
        print(
            json.dumps(
                {
                    "status": "fail",
                    "reason": "missing soak_evidence.json",
                    "path": evidence_path.as_posix(),
                },
                indent=2,
            )
        )
        return 1

    payload = json.loads(evidence_path.read_text(encoding="utf-8"))

    failures: list[str] = []
    if payload.get("result") != "approved":
        failures.append("result must be `approved`")

    duration = float(payload.get("duration_hours", 0.0))
    if duration < 48.0:
        failures.append(f"duration_hours must be >= 48.0 (got {duration})")

    mandatory = payload.get("mandatory_events", {})
    for key in [
        "startup_success",
        "monitoring_loop_per_symbol",
        "health_checks_recorded",
        "error_recovery_events_recorded",
        "shutdown_recorded",
    ]:
        if mandatory.get(key) is not True:
            failures.append(f"mandatory event not satisfied: {key}")

    result = {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "path": evidence_path.as_posix(),
    }
    print(json.dumps(result, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
