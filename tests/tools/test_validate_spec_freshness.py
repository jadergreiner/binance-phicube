from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from tools.validate_spec_freshness import validate_spec_freshness


def _write_spec(path: Path, *, status: str, date_value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# SPEC_X\n\n**Status:** {status}\n**Data:** {date_value}\n",
        encoding="utf-8",
    )


def test_draft_stale_is_error(tmp_path: Path) -> None:
    _write_spec(
        tmp_path / "SPEC_001_EXAMPLE" / "SPEC.md",
        status="Rascunho",
        date_value="2025-01-01",
    )
    issues = validate_spec_freshness(
        base_dir=str(tmp_path),
        max_age_days=90,
        now=datetime(2026, 5, 15, tzinfo=UTC),
    )
    assert any(i.level == "ERROR" for i in issues)


def test_concluded_stale_is_warning(tmp_path: Path) -> None:
    _write_spec(
        tmp_path / "SPEC_002_EXAMPLE" / "SPEC.md",
        status="Concluída",
        date_value="2025-01-01",
    )
    issues = validate_spec_freshness(
        base_dir=str(tmp_path),
        max_age_days=90,
        now=datetime(2026, 5, 15, tzinfo=UTC),
    )
    assert any(i.level == "WARNING" for i in issues)
    assert all(i.level != "ERROR" for i in issues)


def test_recent_spec_has_no_issue(tmp_path: Path) -> None:
    _write_spec(
        tmp_path / "SPEC_003_EXAMPLE" / "SPEC.md",
        status="Rascunho",
        date_value="2026-05-01",
    )
    issues = validate_spec_freshness(
        base_dir=str(tmp_path),
        max_age_days=90,
        now=datetime(2026, 5, 15, tzinfo=UTC),
    )
    assert issues == []
