from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

STATUS_PATTERN = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
DATE_PATTERN = re.compile(r"^\*\*Data:\*\*\s*(\d{4}-\d{2}-\d{2})\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class FreshnessIssue:
    level: str
    file_path: str
    message: str


def _normalize_status(raw: str) -> str:
    return raw.strip().lower()


def _issue_level(status: str, stale_days: int, max_age_days: int) -> str | None:
    if stale_days <= max_age_days:
        return None
    if "rascunho" in status or "draft" in status:
        return "ERROR"
    if "conclu" in status or "done" in status or "complete" in status:
        return "WARNING"
    return "WARNING"


def _parse_file(path: Path) -> tuple[str, datetime] | None:
    content = path.read_text(encoding="utf-8")
    status_match = STATUS_PATTERN.search(content)
    date_match = DATE_PATTERN.search(content)
    if not status_match or not date_match:
        return None
    status = _normalize_status(status_match.group(1))
    parsed_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").replace(tzinfo=UTC)
    return status, parsed_date


def validate_spec_freshness(
    base_dir: str, max_age_days: int, now: datetime | None = None
) -> list[FreshnessIssue]:
    current = now or datetime.now(UTC)
    issues: list[FreshnessIssue] = []
    for spec_file in sorted(Path(base_dir).glob("SPEC_*/SPEC.md")):
        parsed = _parse_file(spec_file)
        if parsed is None:
            issues.append(
                FreshnessIssue(
                    level="WARNING",
                    file_path=str(spec_file),
                    message="arquivo sem metadata de Status/Data parseável",
                )
            )
            continue
        status, date_value = parsed
        stale_days = (current - date_value).days
        level = _issue_level(status=status, stale_days=stale_days, max_age_days=max_age_days)
        if level:
            issues.append(
                FreshnessIssue(
                    level=level,
                    file_path=str(spec_file),
                    message=(
                        f"spec_stale status={status} stale_days={stale_days} "
                        f"max_age_days={max_age_days}"
                    ),
                )
            )
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida freshness de SPECs.")
    parser.add_argument("--base-dir", default="docs/SDD")
    parser.add_argument("--max-age", type=int, default=90)
    args = parser.parse_args()

    issues = validate_spec_freshness(base_dir=args.base_dir, max_age_days=args.max_age)
    has_error = False
    for issue in issues:
        print(f"{issue.level} {issue.file_path} {issue.message}")
        if issue.level == "ERROR":
            has_error = True
    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
