"""Helpers for persistent cache fingerprint tests."""

from __future__ import annotations

import ast
from pathlib import Path
from types import MappingProxyType

from strata.config.core.constants import DEFAULT_THRESHOLDS
from strata.config.core.models import Config
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family, RuleContext, Threshold


def config_with_statement_threshold(*, value: int, reverse_mapping_order: bool) -> Config:
    """Return a config whose threshold mapping has the requested insertion order."""

    thresholds: dict[Threshold, int] = dict(DEFAULT_THRESHOLDS)
    thresholds[Threshold.MAX_STATEMENTS] = value
    items: list[tuple[Threshold, int]] = list(thresholds.items())
    if reverse_mapping_order:
        items.reverse()
    return Config(
        roots=("src/pkg",),
        thresholds=MappingProxyType(dict(items)),
    )


def write_implementation(*, root: Path, source: str) -> None:
    """Write one implementation file below a package root."""

    path: Path = root / "domain/helpers.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def rule_with_message(message: str) -> RuleSpec:
    """Return one deterministic fake rule for ruleset fingerprint tests."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        del module, ctx
        return []

    return RuleSpec(
        code="XCA001",
        family=Family.CUSTOM,
        slug="cache-test",
        message=message,
        check=check,
    )


def write_custom_rule(*, path: Path, returns_fault: bool) -> None:
    """Write one custom rule with stable metadata and selectable behavior."""

    result: str = "[ctx.path_fault()]" if returns_fault else "[]"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "from __future__ import annotations\n\n"
        "import ast\n\n"
        "from strata import Family, Fault, RuleContext, rule\n\n"
        "@rule(code='XCF001', family=Family.CUSTOM, slug='cache-source', message='stable')\n"
        "def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
        "    del module\n"
        f"    return {result}\n",
        encoding="utf-8",
    )
