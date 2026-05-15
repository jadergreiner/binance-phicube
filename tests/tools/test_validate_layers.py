from __future__ import annotations

from pathlib import Path

from tools.validate_layers import validate_layers


def test_layer_violation_detected(tmp_path: Path) -> None:
    src = tmp_path / "src"
    strategy = src / "strategy"
    api = src / "api"
    strategy.mkdir(parents=True, exist_ok=True)
    api.mkdir(parents=True, exist_ok=True)
    (strategy / "foo.py").write_text("from src.api.main import app\n", encoding="utf-8")
    (api / "main.py").write_text("app = object()\n", encoding="utf-8")

    violations = validate_layers(src_dir=str(src))
    assert len(violations) == 1
    assert violations[0].source_layer == "strategy"
    assert violations[0].target_layer == "api"


def test_allowed_common_import(tmp_path: Path) -> None:
    src = tmp_path / "src"
    strategy = src / "strategy"
    common = src / "common"
    strategy.mkdir(parents=True, exist_ok=True)
    common.mkdir(parents=True, exist_ok=True)
    (strategy / "foo.py").write_text("from src.common.result import ok\n", encoding="utf-8")
    (common / "result.py").write_text("def ok(x):\n    return x\n", encoding="utf-8")

    violations = validate_layers(src_dir=str(src))
    assert violations == []
