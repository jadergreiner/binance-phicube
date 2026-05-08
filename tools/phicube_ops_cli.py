#!/usr/bin/env python3
"""Operational CLI for common Phicube workflows."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=True))


def cmd_doctor(args: argparse.Namespace) -> int:
    checks: dict[str, dict[str, str | bool]] = {}
    binaries = ("python", "git", "docker", "gh")
    for binary in binaries:
        checks[f"bin:{binary}"] = {
            "ok": shutil.which(binary) is not None,
            "detail": shutil.which(binary) or "not found",
        }

    required_paths = [
        ROOT / "AGENTS.md",
        ROOT / "PLANS.md",
        ROOT / "code_review.md",
        ROOT / "docs" / "CODEX_TASK_TEMPLATE.md",
        ROOT / "docs" / "CODEX_BEST_PRACTICES_ADOPTION.md",
        ROOT / ".codex" / "config.toml",
        ROOT / ".codex" / "skills" / "gh-fix-ci" / "SKILL.md",
        ROOT / ".codex" / "skills" / "security-threat-model" / "SKILL.md",
        ROOT / ".codex" / "skills" / "cli-creator" / "SKILL.md",
        ROOT / ".github" / "workflows" / "spec021-validation.yml",
        ROOT / ".github" / "workflows" / "spec023-validation.yml",
    ]
    for path in required_paths:
        checks[f"path:{path.relative_to(ROOT)}"] = {"ok": path.exists(), "detail": str(path)}

    ok = all(bool(item["ok"]) for item in checks.values())
    if args.json:
        _print_json({"ok": ok, "checks": checks})
    else:
        for key, item in checks.items():
            status = "OK" if item["ok"] else "FAIL"
            print(f"[{status}] {key} -> {item['detail']}")
        print(f"\nOverall: {'OK' if ok else 'FAIL'}")
    return 0 if ok else 1


def cmd_api_health(args: argparse.Namespace) -> int:
    url = args.url
    try:
        with urllib.request.urlopen(url, timeout=args.timeout) as response:
            payload = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.URLError as exc:
        if args.json:
            _print_json({"ok": False, "url": url, "error": str(exc)})
        else:
            print(f"[FAIL] {url} -> {exc}")
        return 1

    if args.json:
        _print_json({"ok": status == 200, "url": url, "status": status, "payload": payload})
    else:
        print(f"[OK] {url} -> HTTP {status}")
        print(payload)
    return 0 if status == 200 else 1


def cmd_dashboard_logs(args: argparse.Namespace) -> int:
    cmd = ["docker", "compose", "logs", "dashboard-api", f"--tail={args.lines}"]
    result = _run(cmd)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode

    output = result.stdout
    if args.pattern:
        filtered = [line for line in output.splitlines() if args.pattern in line]
        output = "\n".join(filtered)
    print(output)
    return 0


def cmd_ci_inspect(args: argparse.Namespace) -> int:
    script = ROOT / ".codex" / "skills" / "gh-fix-ci" / "scripts" / "inspect_pr_checks.py"
    if not script.exists():
        print(f"Script not found: {script}")
        return 1

    cmd = [sys.executable, str(script), "--repo", str(ROOT)]
    if args.pr:
        cmd.extend(["--pr", args.pr])
    if args.json:
        cmd.append("--json")
    result = _run(cmd)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phicube-ops", description="Phicube operations CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_doctor = sub.add_parser("doctor", help="Check local prerequisites and skill setup")
    p_doctor.add_argument("--json", action="store_true", help="Emit JSON output")
    p_doctor.set_defaults(func=cmd_doctor)

    p_health = sub.add_parser("api-health", help="Check API health endpoint")
    p_health.add_argument("--url", default="http://localhost:8080/health")
    p_health.add_argument("--timeout", type=int, default=5)
    p_health.add_argument("--json", action="store_true", help="Emit JSON output")
    p_health.set_defaults(func=cmd_api_health)

    p_logs = sub.add_parser("dashboard-logs", help="Tail dashboard-api docker logs")
    p_logs.add_argument("--lines", type=int, default=120)
    p_logs.add_argument("--pattern", default=None, help="Filter lines containing this text")
    p_logs.set_defaults(func=cmd_dashboard_logs)

    p_ci = sub.add_parser("ci-inspect", help="Inspect PR checks via gh-fix-ci skill script")
    p_ci.add_argument("--pr", default=None, help="PR number or URL. Uses branch PR if omitted.")
    p_ci.add_argument("--json", action="store_true", help="Emit JSON output from inspector")
    p_ci.set_defaults(func=cmd_ci_inspect)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
