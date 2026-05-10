#!/usr/bin/env python3
"""Generate a repository-grounded threat model markdown file."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

SECRET_TOKENS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "URI", "MONGO")


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _collect_env_like(lines: list[str]) -> list[str]:
    out: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if any(token in key for token in SECRET_TOKENS):
            out.append(key)
    return sorted(set(out))


def _collect_ports(lines: list[str]) -> list[str]:
    ports: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        candidate = stripped.lstrip("-").strip().strip('"').strip("'")
        if ":" in candidate and any(char.isdigit() for char in candidate):
            ports.append(candidate)
    return sorted(set(ports))


def _default_output(repo: Path) -> Path:
    return repo / "reports" / "threat-models" / f"{repo.name}-threat-model.md"


def _render_markdown(
    repo: Path,
    env_keys: list[str],
    ports: list[str],
    has_dashboard: bool,
    has_api: bool,
) -> str:
    now = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    boundaries: list[str] = [
        "Public internet -> Dashboard/API endpoints",
        "Application services -> Binance APIs",
        "Application services -> MongoDB data store",
        "Operator machine/CI runner -> GitHub repository and workflows",
    ]
    assets: list[str] = [
        "Binance credentials (trading and dashboard read-only keys)",
        "Trading signals, order history, and risk parameters",
        "MongoDB stored operational data and audit events",
        "GitHub workflows and repository integrity",
    ]
    components: list[str] = [
        "Trading bot runtime",
        "Docker Compose stack",
        "GitHub Actions workflows",
    ]
    if has_api:
        components.append("FastAPI service endpoints")
    if has_dashboard:
        components.append("Dashboard UI and stream updater")
    ports_text = (
        ", ".join(ports) if ports else "No explicit host ports detected from compose parsing"
    )
    env_text = (
        ", ".join(env_keys) if env_keys else "No sensitive-style env keys detected in .env.example"
    )

    return f"""# Threat Model: {repo.name}

Generated: {now}
Repository: `{repo}`

## Scope And Assumptions

- Scope: repository-level model for runtime, API, dashboard, CI, and deployment artifacts.
- Assumption: project remains single-tenant and GitHub-centric.
- Assumption: production secrets are injected by environment variables and are not committed.

## System Boundaries

Components in scope:
{chr(10).join(f"- {c}" for c in components)}

Trust boundaries:
{chr(10).join(f"- {b}" for b in boundaries)}

Observed host port mappings: {ports_text}

Sensitive environment keys discovered from `.env.example`: {env_text}

## Assets And Threat Actors

Primary assets:
{chr(10).join(f"- {a}" for a in assets)}

Threat actors:
- External attacker probing exposed endpoints and weak auth paths
- Insider or compromised workstation with repository/env access
- Supply-chain attacker via dependencies or CI workflow abuse
- Credential thief targeting Binance or MongoDB secrets

## Prioritized Threats (STRIDE)

- T1 / Spoofing / High
  - Threat: stolen API keys used to submit unauthorized trading actions.
  - Impact: financial loss and account compromise.
  - Mitigations: restrict API scopes, enforce IP whitelist, rotate keys, monitor auth failures.
- T2 / Tampering / High
  - Threat: unauthorized changes to risk logic or order flow through repo or CI manipulation.
  - Impact: silent strategy drift and unsafe execution.
  - Mitigations: branch protection, required reviews, and CI checks on risk modules.
- T3 / Repudiation / Medium
  - Threat: missing audit trace for position or order interventions.
  - Impact: forensic gap after incidents.
  - Mitigations: structured event logging with immutable timestamps and actor/source fields.
- T4 / Information Disclosure / High
  - Threat: secrets leaked in logs, env files, or debug output.
  - Impact: key compromise and data exfiltration.
  - Mitigations: secret scanning, redaction guards, and least-privilege credentials.
- T5 / Denial Of Service / Medium
  - Threat: API/dashboard overload or unstable upstream dependencies.
  - Impact: trading blind spots and stale risk view.
  - Mitigations: timeouts, retries with backoff, health endpoints, graceful degradation.
- T6 / Elevation Of Privilege / High
  - Threat: over-privileged dashboard/API credentials enabling trading privileges.
  - Impact: expanded blast radius from UI/API compromise.
  - Mitigations: separate read-only dashboard keys and strict credential separation.

## Required Follow-up Actions

- Validate T1/T4 controls with `security-audit` before each release.
- Add explicit checklist item for dashboard credential scope verification.
- Ensure CI failure triage flow (`gh-fix-ci`) is part of incident response.
- Re-generate this model after major architecture or deployment changes.
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate threat model markdown for this repository."
    )
    parser.add_argument("--repo", default=".", help="Repository root path.")
    parser.add_argument("--output", default=None, help="Output markdown file path.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite output if it exists.")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    output = Path(args.output).resolve() if args.output else _default_output(repo)
    compose_lines = _read_lines(repo / "docker-compose.yml")
    env_lines = _read_lines(repo / ".env.example")

    env_keys = _collect_env_like(env_lines)
    ports = _collect_ports(compose_lines)
    has_dashboard = (repo / "src" / "dashboard").exists()
    has_api = (repo / "src" / "api").exists()
    markdown = _render_markdown(repo, env_keys, ports, has_dashboard, has_api)

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.overwrite:
        raise FileExistsError(
            f"Output file already exists: {output}. Use --overwrite to replace it."
        )
    output.write_text(markdown, encoding="utf-8")
    print(f"[ok] threat model generated at: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
