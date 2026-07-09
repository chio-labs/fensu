"""Helpers for ruleset registry tests."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family, RuleContext


def write_custom_rule_file(
    *, root: Path, relative_path: str, rule_code: str, prelude: str = ""
) -> Path:
    """Write a custom rule file that registers one no-op rule."""

    path: Path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_custom_rule_source(rule_code=rule_code, prelude=prelude), encoding="utf-8")
    return path


def write_module_package(*, root: Path, package_name: str, rule_code: str) -> str:
    """Write an importable package containing one custom rule module."""

    package_path: Path = root / package_name
    package_path.mkdir(parents=True, exist_ok=True)
    (package_path / "__init__.py").write_text(
        _custom_rule_source(rule_code=rule_code), encoding="utf-8"
    )
    return package_name


def make_core_rule(*, code: str, family: Family, enabled_by_default: bool = True) -> RuleSpec:
    """Build a fake core rule for selection-composition tests."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        return []

    return RuleSpec(
        code=code,
        family=family,
        slug=f"rule-{code.lower()}",
        message=code,
        check=check,
        enabled_by_default=enabled_by_default,
    )


def _custom_rule_source(*, rule_code: str, prelude: str = "") -> str:
    family: str = "Family.CUSTOM" if rule_code.startswith("X") else "Family.LAYERS"
    return f'''
from __future__ import annotations

import ast

from strata import Family, Fault, RuleContext, rule

{prelude}

@rule(code="{rule_code}", family={family}, slug="custom-rule", message="custom message")
def custom_rule(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    return []
'''
