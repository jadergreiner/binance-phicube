from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path

ALWAYS_ALLOWED_PREFIXES = (
    "src.common",
    "src.config",
    "src.monitoring",
    "src.resilience",
)

LAYER_IMPORT_RULES: dict[str, set[str]] = {
    "strategy": {"strategy", "monitoring", "common", "config"},
    "trading": {
        "trading",
        "strategy",
        "exchange",
        "notifications",
        "monitoring",
        "storage",
        "common",
        "config",
        "resilience",
    },
    "api": {
        "api",
        "storage",
        "strategy",
        "monitoring",
        "common",
        "config",
        "backtest",
        "exchange",
        "trading",
        "dashboard",
    },
    "exchange": {"exchange", "monitoring", "common", "config", "resilience"},
    "storage": {
        "storage",
        "monitoring",
        "common",
        "config",
        "trading",
        "strategy",
        "notifications",
    },
    "notifications": {"notifications", "monitoring", "common", "config", "storage"},
    "backtest": {"backtest", "strategy", "trading", "exchange", "common", "config", "monitoring"},
}


@dataclass(frozen=True)
class LayerViolation:
    file_path: str
    source_layer: str
    target_layer: str
    import_stmt: str


def _layer_from_path(file_path: Path) -> str | None:
    parts = file_path.parts
    if "src" not in parts:
        return None
    idx = parts.index("src")
    if idx + 1 >= len(parts):
        return None
    return parts[idx + 1]


def _layer_from_module(module_name: str) -> str | None:
    if not module_name.startswith("src."):
        return None
    segments = module_name.split(".")
    if len(segments) < 2:
        return None
    return segments[1]


def _extract_imports(file_path: Path) -> list[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _is_allowed(source_layer: str, module_name: str) -> bool:
    if not module_name.startswith("src."):
        return True
    if module_name.startswith(ALWAYS_ALLOWED_PREFIXES):
        return True
    target_layer = _layer_from_module(module_name)
    if target_layer is None:
        return True
    allowed = LAYER_IMPORT_RULES.get(source_layer)
    if allowed is None:
        return True
    return target_layer in allowed


def validate_layers(src_dir: str = "src") -> list[LayerViolation]:
    violations: list[LayerViolation] = []
    for file_path in sorted(Path(src_dir).rglob("*.py")):
        source_layer = _layer_from_path(file_path)
        if source_layer is None:
            continue
        for imported in _extract_imports(file_path):
            if _is_allowed(source_layer, imported):
                continue
            target_layer = _layer_from_module(imported) or "unknown"
            violations.append(
                LayerViolation(
                    file_path=str(file_path),
                    source_layer=source_layer,
                    target_layer=target_layer,
                    import_stmt=imported,
                )
            )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida fronteiras de camadas por imports.")
    parser.add_argument("--src-dir", default="src")
    args = parser.parse_args()

    violations = validate_layers(src_dir=args.src_dir)
    for violation in violations:
        print(
            "ERROR layer_violation "
            f"file={violation.file_path} source={violation.source_layer} "
            f"target={violation.target_layer} import={violation.import_stmt}"
        )
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
