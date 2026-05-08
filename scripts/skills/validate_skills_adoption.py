#!/usr/bin/env python3
"""Validate prioritized skills adoption scenarios for Phicube."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIORITIZED_SKILLS = ("gh-fix-ci", "security-threat-model", "cli-creator")
MAX_LOCAL_DESCRIPTIONS_CHARS = 7000


def run_step(name: str, command: list[str]) -> tuple[bool, str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    ok = result.returncode == 0
    output = (result.stdout + result.stderr).strip()
    return ok, f"{name}: {'OK' if ok else 'FAIL'}\n{output}\n"


def check_codex_artifacts() -> tuple[bool, str]:
    required_files = [
        ROOT / "AGENTS.md",
        ROOT / "PLANS.md",
        ROOT / "code_review.md",
        ROOT / "docs" / "CODEX_TASK_TEMPLATE.md",
        ROOT / "docs" / "CODEX_BEST_PRACTICES_ADOPTION.md",
        ROOT / ".codex" / "config.toml",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required_files if not path.exists()]
    if missing:
        return (
            False,
            "Scenario 4 / codex best-practices artifacts: FAIL\n" + "\n".join(missing),
        )

    required_markers: dict[Path, list[str]] = {
        ROOT / "AGENTS.md": ["Done when", "Puxao de orelha operacional"],
        ROOT / "PLANS.md": ["Problema", "Criterio de pronto"],
        ROOT / "code_review.md": ["Checklist de review", "Testes e validacao"],
        ROOT / "docs" / "CODEX_TASK_TEMPLATE.md": [
            "Goal:",
            "Done when:",
            "Puxao de orelha",
        ],
        ROOT / "docs" / "CODEX_BEST_PRACTICES_ADOPTION.md": [
            "Mapeamento das recomendacoes oficiais",
            "Erros comuns que o time deve evitar",
        ],
    }

    missing_markers: list[str] = []
    for path, markers in required_markers.items():
        content = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in content:
                missing_markers.append(f"{path.relative_to(ROOT)} -> marker ausente: {marker}")

    if missing_markers:
        return (
            False,
            "Scenario 4 / codex best-practices artifacts: FAIL\n" + "\n".join(missing_markers),
        )

    return True, "Scenario 4 / codex best-practices artifacts: OK"


def _extract_frontmatter(skill_path: Path) -> tuple[dict[str, str], str]:
    content = skill_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    metadata: dict[str, str] = {}
    frontmatter = parts[1]
    body = parts[2]
    for line in frontmatter.splitlines():
        match = re.match(r"^\s*([a-zA-Z0-9_-]+)\s*:\s*(.+?)\s*$", line)
        if not match:
            continue
        key, value = match.group(1), match.group(2)
        if key in {"name", "description"}:
            metadata[key] = value

    return metadata, body


def check_skill_recommendations() -> tuple[bool, str]:
    failures: list[str] = []
    for skill_name in PRIORITIZED_SKILLS:
        skill_path = ROOT / ".codex" / "skills" / skill_name / "SKILL.md"
        if not skill_path.exists():
            failures.append(f".codex/skills/{skill_name}/SKILL.md ausente")
            continue

        metadata, body = _extract_frontmatter(skill_path)
        description = metadata.get("description", "")
        registered_name = metadata.get("name", "")

        if registered_name != skill_name:
            failures.append(f"{skill_name}: frontmatter name inconsistente")
        if not description:
            failures.append(f"{skill_name}: frontmatter description ausente")
        if len(description) > 320:
            failures.append(f"{skill_name}: description longa demais ({len(description)} chars)")
        if "use when" not in description.lower():
            failures.append(f"{skill_name}: description sem gatilho explicito `Use when`")
        if "workflow" not in body.lower():
            failures.append(f"{skill_name}: corpo sem secao de workflow")
        if "input" not in body.lower() and "when to use" not in body.lower():
            failures.append(f"{skill_name}: corpo sem entradas ou criterio de uso")

    local_skill_paths = sorted((ROOT / ".codex" / "skills").glob("*/SKILL.md"))
    total_description_chars = 0
    for skill_path in local_skill_paths:
        metadata, _ = _extract_frontmatter(skill_path)
        total_description_chars += len(metadata.get("description", ""))
    if total_description_chars > MAX_LOCAL_DESCRIPTIONS_CHARS:
        failures.append(
            "orcamento de descricoes locais acima do limite recomendado "
            f"({total_description_chars} > {MAX_LOCAL_DESCRIPTIONS_CHARS})"
        )

    if failures:
        return (
            False,
            "Scenario 5 / skills recommendations compliance: FAIL\n" + "\n".join(failures),
        )

    return True, "Scenario 5 / skills recommendations compliance: OK"


def main() -> int:
    steps = [
        (
            "Scenario 1 / gh-fix-ci help smoke",
            [sys.executable, ".codex/skills/gh-fix-ci/scripts/inspect_pr_checks.py", "--help"],
        ),
        (
            "Scenario 2 / threat model generation",
            [
                sys.executable,
                ".codex/skills/security-threat-model/scripts/generate_threat_model.py",
                "--repo",
                ".",
                "--overwrite",
            ],
        ),
        (
            "Scenario 3 / ops CLI doctor",
            [sys.executable, "tools/phicube_ops_cli.py", "doctor", "--json"],
        ),
    ]

    results = []
    failed = 0
    for name, cmd in steps:
        ok, msg = run_step(name, cmd)
        results.append(msg)
        if not ok:
            failed += 1

    artifacts_ok, artifacts_msg = check_codex_artifacts()
    results.append(artifacts_msg)
    if not artifacts_ok:
        failed += 1

    skills_ok, skills_msg = check_skill_recommendations()
    results.append(skills_msg)
    if not skills_ok:
        failed += 1

    print("\n".join(results))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
