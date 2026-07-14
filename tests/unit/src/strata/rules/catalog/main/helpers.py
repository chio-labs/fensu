"""Helpers for ruleset registry tests."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family, RuleContext, RuleKind


def write_custom_rule_file(
    *,
    root: Path,
    relative_path: str,
    rule_code: str,
    prelude: str = "",
    check_body: str = "    return []",
    decorator_arguments: str = "",
) -> Path:
    """Write a custom rule file that registers one no-op rule."""

    path: Path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _custom_rule_source(
            rule_code=rule_code,
            prelude=prelude,
            check_body=check_body,
            decorator_arguments=decorator_arguments,
        ),
        encoding="utf-8",
    )
    return path


def write_direct_custom_rule_file(
    *,
    root: Path,
    rule_code: object,
    kind: RuleKind,
    family_expression: str = "Family.CUSTOM",
    cacheable: bool = False,
) -> Path:
    """Write a custom source that attaches a directly constructed RuleSpec."""

    path: Path = root / "rules/direct_rule.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""from __future__ import annotations

from strata import Family
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import RuleKind


def check(module, ctx):
    return []


check.__strata_rule_spec__ = RuleSpec(
    code={rule_code!r},
    family={family_expression},
    slug="direct-rule",
    message="direct rule",
    check=check,
    kind=RuleKind.{kind.name},
    cacheable={cacheable!r},
)
""",
        encoding="utf-8",
    )
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
    helper_path: Path = package / "_helpers/names.py"
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

from scripts.strata_rules._helpers.names import RULE_MESSAGE
from strata import Family, Fault, RuleContext, rule


@rule(code="{rule_code}", family=Family.CUSTOM, slug="custom-rule", message=RULE_MESSAGE)
def custom_rule(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    return []
''',
        encoding="utf-8",
    )
    return rules_path.parent


def rule_by_code(*, rules: tuple[RuleSpec, ...], code: str) -> RuleSpec:
    """Return the single catalogue rule carrying one exact code."""

    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in rules}
    return rules_by_code[code]


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
        kind={False: RuleKind.CUSTOM, True: RuleKind.CORE}[code.startswith("SF")],
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
        remediation: str = rule.remediation or ""
        issues.extend(
            {False: (), True: (f"{rule.code}: missing remediation",)}[rule.remediation is None]
        )
        issues.extend(
            {False: (), True: (f"{rule.code}: message too long",)}[
                len(rule.message) > max_message_length
            ]
        )
        issues.extend(
            {False: (), True: (f"{rule.code}: remediation too long",)}[
                len(remediation) > max_remediation_length
            ]
        )
        for fragment in forbidden_message_fragments:
            issues.extend(
                {False: (), True: (f"{rule.code}: generic message",)}[fragment in rule.message]
            )
    return tuple(issues)


def _custom_rule_source(
    *,
    rule_code: str,
    prelude: str = "",
    check_body: str = "    return []",
    decorator_arguments: str = "",
) -> str:
    family: str = {False: "Family.LAYERS", True: "Family.CUSTOM"}[rule_code.startswith("X")]
    envelope: str = (
        f'code="{rule_code}", family={family}, slug="custom-rule", '
        f'message="custom message"{decorator_arguments}'
    )
    return f"""
from __future__ import annotations

import ast

from strata import Family, Fault, RuleContext, rule

{prelude}

@rule({envelope})
def custom_rule(module: ast.Module, ctx: RuleContext) -> list[Fault]:
{check_body}
"""
