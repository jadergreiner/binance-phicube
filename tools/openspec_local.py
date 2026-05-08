#!/usr/bin/env python3
"""OpenSpec local compat tool (subset) for offline/spec-driven workflow."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENSPEC_DIR = ROOT / "openspec"
SPECS_DIR = OPENSPEC_DIR / "specs"
CHANGES_DIR = OPENSPEC_DIR / "changes"
ARCHIVE_DIR = CHANGES_DIR / "archive"


@dataclass(frozen=True)
class ChangePaths:
    slug: str
    root: Path
    proposal: Path
    design: Path
    tasks: Path
    specs_dir: Path


def _slugify(value: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return base or "change"


def _print(data: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=True))
        return
    for key, value in data.items():
        if isinstance(value, list | dict):
            print(f"{key}: {json.dumps(value, ensure_ascii=True)}")
        else:
            print(f"{key}: {value}")


def _ensure_openspec_initialized() -> tuple[bool, str]:
    if not OPENSPEC_DIR.exists():
        return (
            False,
            "OpenSpec nao inicializado. Rode: python tools/openspec_local.py init",
        )
    return True, ""


def _change_paths(slug: str) -> ChangePaths:
    root = CHANGES_DIR / slug
    return ChangePaths(
        slug=slug,
        root=root,
        proposal=root / "proposal.md",
        design=root / "design.md",
        tasks=root / "tasks.md",
        specs_dir=root / "specs",
    )


def cmd_init(args: argparse.Namespace) -> int:
    OPENSPEC_DIR.mkdir(parents=True, exist_ok=True)
    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    CHANGES_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    config = OPENSPEC_DIR / "config.yaml"
    if not config.exists():
        config.write_text(
            "profile: core\n"
            "delivery: both\n"
            "workflows:\n"
            "  - propose\n"
            "  - explore\n"
            "  - apply\n"
            "  - archive\n",
            encoding="utf-8",
        )
    result = {
        "ok": True,
        "created": [
            str(OPENSPEC_DIR),
            str(SPECS_DIR),
            str(CHANGES_DIR),
            str(ARCHIVE_DIR),
            str(config),
        ],
    }
    _print(result, args.json)
    return 0


def cmd_propose(args: argparse.Namespace) -> int:
    ok, msg = _ensure_openspec_initialized()
    if not ok:
        print(msg)
        return 1
    slug = _slugify(args.name)
    paths = _change_paths(slug)
    if paths.root.exists():
        print(f"Change ja existe: {paths.root}")
        return 1
    paths.root.mkdir(parents=True, exist_ok=False)
    paths.specs_dir.mkdir(parents=True, exist_ok=True)

    title = args.title or args.name.strip()
    domain = _slugify(args.domain or "geral")
    domain_spec = paths.specs_dir / domain
    domain_spec.mkdir(parents=True, exist_ok=True)

    paths.proposal.write_text(
        f"# Proposal: {title}\n\n"
        "## Intent\n"
        "- Descreva o objetivo de negocio.\n\n"
        "## Scope\n"
        "- Defina o que entra e o que nao entra.\n\n"
        "## Approach\n"
        "- Descreva o caminho tecnico inicial.\n",
        encoding="utf-8",
    )
    paths.design.write_text(
        f"# Design: {title}\n\n"
        "## Arquitetura\n"
        "- Componentes impactados\n\n"
        "## Decisoes tecnicas\n"
        "- Tradeoffs e riscos\n",
        encoding="utf-8",
    )
    paths.tasks.write_text(
        "# Tasks\n\n"
        "## 1. Planejamento\n"
        "- [ ] 1.1 Refinar proposal\n"
        "- [ ] 1.2 Definir delta de spec\n\n"
        "## 2. Implementacao\n"
        "- [ ] 2.1 Implementar codigo\n"
        "- [ ] 2.2 Cobrir com testes\n\n"
        "## 3. Validacao\n"
        "- [ ] 3.1 Rodar lint/testes\n"
        "- [ ] 3.2 Atualizar status\n",
        encoding="utf-8",
    )
    (domain_spec / "spec.md").write_text(
        f"# Delta for {domain}\n\n"
        "## ADDED Requirements\n\n"
        "### Requirement: [Nome do requisito]\n"
        "O sistema DEVE ...\n\n"
        "#### Scenario: [Cenario principal]\n"
        "- GIVEN ...\n"
        "- WHEN ...\n"
        "- THEN ...\n",
        encoding="utf-8",
    )

    result = {
        "ok": True,
        "change": slug,
        "path": str(paths.root),
        "files": [
            str(paths.proposal),
            str(paths.design),
            str(paths.tasks),
            str(domain_spec / "spec.md"),
        ],
    }
    _print(result, args.json)
    return 0


def _active_changes() -> list[Path]:
    if not CHANGES_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in CHANGES_DIR.iterdir()
            if p.is_dir() and p.name != "archive"
        ],
        key=lambda p: p.name,
    )


def cmd_list(args: argparse.Namespace) -> int:
    ok, msg = _ensure_openspec_initialized()
    if not ok:
        print(msg)
        return 1
    changes = [p.name for p in _active_changes()]
    specs = [p.name for p in sorted(SPECS_DIR.iterdir()) if p.is_dir()]
    _print({"ok": True, "changes": changes, "spec_domains": specs}, args.json)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    ok, msg = _ensure_openspec_initialized()
    if not ok:
        print(msg)
        return 1
    slug = _slugify(args.item)
    paths = _change_paths(slug)
    if not paths.root.exists():
        print(f"Change nao encontrado: {slug}")
        return 1
    data = {
        "ok": True,
        "change": slug,
        "proposal": str(paths.proposal),
        "design": str(paths.design),
        "tasks": str(paths.tasks),
        "specs_dir": str(paths.specs_dir),
    }
    _print(data, args.json)
    return 0


def _validate_change(paths: ChangePaths) -> list[str]:
    errors: list[str] = []
    required = [paths.proposal, paths.design, paths.tasks]
    for req in required:
        if not req.exists():
            errors.append(f"arquivo ausente: {req}")
    spec_files = (
        list(paths.specs_dir.rglob("spec.md")) if paths.specs_dir.exists() else []
    )
    if not spec_files:
        errors.append(f"nenhum delta spec encontrado em: {paths.specs_dir}")
    if paths.tasks.exists():
        body = paths.tasks.read_text(encoding="utf-8", errors="replace")
        if "- [ ]" not in body and "- [x]" not in body:
            errors.append("tasks.md sem checklist")
    return errors


def cmd_validate(args: argparse.Namespace) -> int:
    ok, msg = _ensure_openspec_initialized()
    if not ok:
        print(msg)
        return 1
    targets: list[Path]
    if args.all:
        targets = _active_changes()
    elif args.item:
        targets = [_change_paths(_slugify(args.item)).root]
    else:
        print("Informe --all ou <item>")
        return 1

    report: dict[str, list[str]] = {}
    has_error = False
    for root in targets:
        paths = _change_paths(root.name)
        if not root.exists():
            report[root.name] = ["change nao encontrado"]
            has_error = True
            continue
        errs = _validate_change(paths)
        if errs:
            has_error = True
        report[root.name] = errs
    _print({"ok": not has_error, "report": report}, args.json)
    return 0 if not has_error else 1


def cmd_status(args: argparse.Namespace) -> int:
    ok, msg = _ensure_openspec_initialized()
    if not ok:
        print(msg)
        return 1
    summary: dict[str, dict[str, int]] = {}
    for root in _active_changes():
        tasks = root / "tasks.md"
        done = 0
        todo = 0
        if tasks.exists():
            body = tasks.read_text(encoding="utf-8", errors="replace")
            done = len(re.findall(r"- \[x\]", body, flags=re.IGNORECASE))
            todo = len(re.findall(r"- \[ \]", body))
        summary[root.name] = {"done": done, "todo": todo}
    _print({"ok": True, "status": summary}, args.json)
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    ok, msg = _ensure_openspec_initialized()
    if not ok:
        print(msg)
        return 1
    slug = _slugify(args.item)
    paths = _change_paths(slug)
    if not paths.root.exists():
        print(f"Change nao encontrado: {slug}")
        return 1
    errors = _validate_change(paths)
    if errors and not args.force:
        _print({"ok": False, "change": slug, "errors": errors}, args.json)
        return 1

    if paths.specs_dir.exists():
        for delta_spec in paths.specs_dir.rglob("spec.md"):
            rel = delta_spec.relative_to(paths.specs_dir)
            target = SPECS_DIR / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                delta_spec.read_text(encoding="utf-8", errors="replace"),
                encoding="utf-8",
            )

    timestamp = datetime.now().strftime("%Y-%m-%d")
    archive_target = ARCHIVE_DIR / f"{timestamp}-{slug}"
    archive_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(paths.root), str(archive_target))
    _print({"ok": True, "change": slug, "archived_to": str(archive_target)}, args.json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openspec-local",
        description="OpenSpec local compat (subset)",
    )
    parser.add_argument("--json", action="store_true", help="Saida JSON quando aplicavel")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Inicializa estrutura openspec/")
    p_init.set_defaults(func=cmd_init)

    p_propose = sub.add_parser("propose", help="Cria um change com artefatos base")
    p_propose.add_argument("name", help="Nome do change (slug ou frase)")
    p_propose.add_argument("--title", default=None, help="Titulo amigavel opcional")
    p_propose.add_argument("--domain", default="geral", help="Dominio para delta spec")
    p_propose.set_defaults(func=cmd_propose)

    p_list = sub.add_parser("list", help="Lista changes ativos e dominios")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Mostra caminhos de um change")
    p_show.add_argument("item", help="Nome do change")
    p_show.set_defaults(func=cmd_show)

    p_validate = sub.add_parser("validate", help="Valida artefatos obrigatorios")
    p_validate.add_argument("item", nargs="?", default=None, help="Nome do change")
    p_validate.add_argument(
        "--all",
        action="store_true",
        help="Valida todos os changes ativos",
    )
    p_validate.set_defaults(func=cmd_validate)

    p_status = sub.add_parser("status", help="Resumo de progresso por tasks.md")
    p_status.set_defaults(func=cmd_status)

    p_archive = sub.add_parser("archive", help="Arquiva change e promove specs")
    p_archive.add_argument("item", help="Nome do change")
    p_archive.add_argument(
        "--force",
        action="store_true",
        help="Arquivar mesmo com erros de validacao",
    )
    p_archive.set_defaults(func=cmd_archive)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
