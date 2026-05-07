from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


DOCKERFILES = [Path("docker/Dockerfile"), Path("docker/Dockerfile.api")]
SECRET_PATTERNS = ["API_KEY", "API_SECRET", "TOKEN", "PASSWORD"]
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(API_KEY|API_SECRET|TOKEN|PASSWORD)\b\s*[:=]\s*[\"']([A-Za-z0-9_\-]{12,})[\"']"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_docker_non_root() -> tuple[str, str]:
    failures = []
    for dockerfile in DOCKERFILES:
        if not dockerfile.exists():
            failures.append(f"missing file: {dockerfile.as_posix()}")
            continue
        content = _read(dockerfile)
        if "USER phicube" not in content:
            failures.append(f"{dockerfile.as_posix()} missing `USER phicube`")
    if failures:
        return "fail", "; ".join(failures)
    return "pass", "all runtime dockerfiles use non-root user"


def check_docker_healthcheck() -> tuple[str, str]:
    failures = []
    for dockerfile in DOCKERFILES:
        if not dockerfile.exists():
            failures.append(f"missing file: {dockerfile.as_posix()}")
            continue
        content = _read(dockerfile)
        if "HEALTHCHECK" not in content:
            failures.append(f"{dockerfile.as_posix()} missing HEALTHCHECK")
    if failures:
        return "fail", "; ".join(failures)
    return "pass", "all runtime dockerfiles define HEALTHCHECK"


def check_tracked_secret_literals() -> tuple[str, str]:
    cmd = ["git", "ls-files"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    tracked_files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    allowed_ext = (".py", ".md", ".json", ".yml", ".yaml", ".toml", ".txt", ".sh", ".ps1")

    flagged: list[str] = []
    for rel in tracked_files:
        if not rel.endswith(allowed_ext):
            continue
        path = Path(rel)
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if ".env.example" in rel.lower():
            continue
        for match in SECRET_ASSIGNMENT_RE.finditer(content):
            key_name = match.group(1)
            value = match.group(2)
            if value.lower() in {"changeme", "your_token_here", "your_api_key_here"}:
                continue
            flagged.append(f"{rel} contains suspicious hardcoded secret `{key_name}`")
            break

    if flagged:
        return "fail", "; ".join(flagged[:10])
    return "pass", "no obvious hardcoded secret assignments in tracked text files"


def main() -> int:
    checks: list[dict[str, str]] = []
    failures: list[str] = []

    for check_id, fn in [
        ("HARD-001", check_docker_non_root),
        ("HARD-002", check_docker_healthcheck),
        ("HARD-003", check_tracked_secret_literals),
    ]:
        status, details = fn()
        checks.append({"id": check_id, "status": status, "details": details})
        if status == "fail":
            failures.append(f"{check_id}: {details}")

    result = {
        "status": "pass" if not failures else "fail",
        "checks": checks,
        "failures": failures,
    }

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir / "spec021_hardening_report.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
