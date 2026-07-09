"""Helpers for CLI tests."""

from __future__ import annotations

from io import StringIO
from pathlib import Path


class CaptureOutput(StringIO):
    """Small text sink with configurable terminal-color support."""

    def __init__(self, *, is_terminal: bool = False) -> None:
        super().__init__()
        self._is_terminal: bool = is_terminal

    def isatty(self) -> bool:
        return self._is_terminal


def write_cli_fixture_project(*, root: Path, rule_code: str) -> None:
    """Write a tiny project with one custom rule that always reports a fault."""

    (root / "src" / "pkg").mkdir(parents=True)
    (root / "rules").mkdir()
    (root / "src" / "pkg" / "target.py").write_text("value: int = 1\n", encoding="utf-8")
    (root / "strata.toml").write_text(
        (f'roots = ["src"]\nselect = ["{rule_code}"]\nrule_paths = ["rules/custom_rule.py"]\n'),
        encoding="utf-8",
    )
    (root / "rules" / "custom_rule.py").write_text(
        f'''
from __future__ import annotations

import ast

from strata import Family, Fault, RuleContext, rule


@rule(code="{rule_code}", family=Family.CUSTOM, slug="always", message="custom fault")
def always(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    return [ctx.fault(module.body[0])]
''',
        encoding="utf-8",
    )


def write_cli_no_fault_project(root: Path) -> None:
    """Write a tiny project with no selected rules."""

    source_dir: Path = root / "src" / "pkg" / "core"
    source_dir.mkdir(parents=True)
    (source_dir / "constants.py").write_text("VALUE: int = 1\n", encoding="utf-8")
    (root / "strata.toml").write_text('roots = ["src"]\n', encoding="utf-8")
