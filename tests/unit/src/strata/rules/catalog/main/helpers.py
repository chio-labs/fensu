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


def write_importing_custom_rule_package(*, root: Path, rule_code: str) -> Path:
    """Write a scripts rule package whose decorated rule imports a local helper."""

    package: Path = root / "scripts/strata_rules"
    rules_path: Path = package / "rules/custom.py"
    helper_path: Path = package / "helpers/names.py"
    rules_path.parent.mkdir(parents=True)
    helper_path.parent.mkdir(parents=True)
    for init_path in (
        root / "scripts/__init__.py",
        package / "__init__.py",
        rules_path.parent / "__init__.py",
        helper_path.parent / "__init__.py",
    ):
        init_path.write_text('"""Package."""\n', encoding="utf-8")
    helper_path.write_text('RULE_MESSAGE: str = "custom message"\n', encoding="utf-8")
    rules_path.write_text(
        f'''
from __future__ import annotations

import ast

from scripts.strata_rules.helpers.names import RULE_MESSAGE
from strata import Family, Fault, RuleContext, rule


@rule(code="{rule_code}", family=Family.CUSTOM, slug="custom-rule", message=RULE_MESSAGE)
def custom_rule(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    return []
''',
        encoding="utf-8",
    )
    return rules_path.parent


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


def catalogue_quality_issues(
    *,
    rules: tuple[RuleSpec, ...],
    forbidden_message_fragments: tuple[str, ...],
    max_message_length: int,
    max_remediation_length: int,
) -> tuple[str, ...]:
    """Return actionable metadata defects from core rules."""

    issues: list[str] = []
    for rule in rules:
        if rule.remediation is None:
            issues.append(f"{rule.code}: missing remediation")
        if len(rule.message) > max_message_length:
            issues.append(f"{rule.code}: message too long")
        if rule.remediation is not None and len(rule.remediation) > max_remediation_length:
            issues.append(f"{rule.code}: remediation too long")
        for fragment in forbidden_message_fragments:
            if fragment in rule.message:
                issues.append(f"{rule.code}: generic message")
    return tuple(issues)


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
