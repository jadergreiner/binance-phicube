from __future__ import annotations

from pathlib import Path

from tools.validate_env_example import (
    extract_settings_fields,
    parse_env_example,
    validate_env_example,
)


def test_parse_env_example_reads_keys(tmp_path: Path) -> None:
    env = tmp_path / ".env.example"
    env.write_text(
        "# comment\nBINANCE_API_KEY=abc\n\nBINANCE_API_SECRET=def\n",
        encoding="utf-8",
    )
    keys = parse_env_example(str(env))
    assert keys == {"BINANCE_API_KEY", "BINANCE_API_SECRET"}


def test_validate_env_example_detects_missing_required(tmp_path: Path) -> None:
    env = tmp_path / ".env.example"
    env.write_text("BINANCE_API_KEY=abc\n", encoding="utf-8")
    report = validate_env_example(path=str(env))
    assert "BINANCE_API_SECRET" in report.missing_required
    assert report.has_errors is True


def test_validate_env_example_detects_extra_key(tmp_path: Path) -> None:
    env = tmp_path / ".env.example"
    env.write_text(
        "BINANCE_API_KEY=abc\nBINANCE_API_SECRET=def\nDASHBOARD_API_KEY=a\nDASHBOARD_API_SECRET=b\n"
        "UNKNOWN_FOO=bar\n",
        encoding="utf-8",
    )
    report = validate_env_example(path=str(env))
    assert "UNKNOWN_FOO" in report.extra_variables


def test_extract_settings_fields_has_expected_required() -> None:
    required, all_fields = extract_settings_fields()
    assert "BINANCE_API_KEY" in required
    assert "BINANCE_API_SECRET" in required
    assert "MONGODB_URI" in all_fields
