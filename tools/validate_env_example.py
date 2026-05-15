from __future__ import annotations

import argparse
from dataclasses import dataclass

from src.config.settings import Settings

IGNORED_ENV_KEYS = {
    "MONGO_INITDB_ROOT_USERNAME",
    "MONGO_INITDB_ROOT_PASSWORD",
    "LEVERAGE",
    "CONTEXT7_API_KEY",
}


@dataclass(frozen=True)
class ValidationReport:
    missing_required: set[str]
    extra_variables: set[str]

    @property
    def has_errors(self) -> bool:
        return bool(self.missing_required)


def _to_env_key(field_name: str) -> str:
    return field_name.upper()


def parse_env_example(path: str) -> set[str]:
    keys: set[str] = set()
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key = line.split("=", 1)[0].strip()
            if key:
                keys.add(key)
    return keys


def extract_settings_fields() -> tuple[set[str], set[str]]:
    required: set[str] = set()
    all_fields: set[str] = set()
    for name, field in Settings.model_fields.items():
        env_key = _to_env_key(name)
        all_fields.add(env_key)
        if field.is_required():
            required.add(env_key)
    return required, all_fields


def validate_env_example(path: str = ".env.example") -> ValidationReport:
    env_keys = parse_env_example(path)
    required, all_fields = extract_settings_fields()
    missing_required = required - env_keys
    extra_variables = (env_keys - all_fields) - IGNORED_ENV_KEYS
    return ValidationReport(
        missing_required=missing_required,
        extra_variables=extra_variables,
    )


def _print_report(report: ValidationReport) -> None:
    for key in sorted(report.missing_required):
        print(f"ERROR missing_required_env_example_key: {key}")
    for key in sorted(report.extra_variables):
        print(f"WARNING unknown_env_example_key: {key}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida sincronização entre .env.example e Settings."
    )
    parser.add_argument("--path", default=".env.example")
    args = parser.parse_args()

    report = validate_env_example(path=args.path)
    _print_report(report)
    if report.has_errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
