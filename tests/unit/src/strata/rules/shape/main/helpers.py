"""Helpers for shape rule tests."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from strata.config.constants import DEFAULT_THRESHOLDS
from strata.config.models import Config
from strata.discovery.main.discover_files import discover_files
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.models import EvaluationResult
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Threshold
from strata.rules.shape.constants import SFS_RULES
from tests.unit.src.strata.rules.shape.main._test_types import ShapeRuleTestCase


def evaluate_shape_test_case(
    *, test_case: ShapeRuleTestCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> EvaluationResult:
    """Write a source file and evaluate a single shape rule."""

    source_root: Path = tmp_path / test_case.root
    path: Path = source_root / test_case.relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(test_case.source, encoding="utf-8")
    for relative_path, source in test_case.project_files:
        project_path: Path = source_root / relative_path
        project_path.parent.mkdir(parents=True, exist_ok=True)
        project_path.write_text(source, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    thresholds: dict[Threshold, int] = dict(DEFAULT_THRESHOLDS)
    thresholds.update(test_case.thresholds)
    config: Config = Config(
        roots=(test_case.root,),
        tests=(),
        thresholds=MappingProxyType(thresholds),
        role_thresholds=MappingProxyType(
            {role: MappingProxyType(values) for role, values in test_case.role_thresholds.items()}
        ),
        threshold_overrides=test_case.threshold_overrides,
    )
    ruleset: tuple[RuleSpec, ...] = (
        SFS_RULES if test_case.rule_code == "SFS" else (_rule_by_code(test_case.rule_code),)
    )
    return evaluate(
        tree=discover_files(config=config),
        ruleset=ruleset,
        config=config,
    )


def statements_source(count: int) -> str:
    """Build a function with the requested number of body statements."""

    body: str = "".join(f"    value_{index}: int = {index}\n" for index in range(count - 1))
    return f"def run() -> None:\n{body}    return None\n"


def method_statements_source(count: int) -> str:
    """Build a class method with the requested number of body statements."""

    method: str = "".join(f"    {line}\n" for line in statements_source(count).splitlines())
    return f"class Service:\n{method}"


def pass_statements_source(count: int) -> str:
    """Build a function with the requested number of statements and no local bindings."""

    body: str = "    pass\n" * (count - 1)
    return f"def run() -> None:\n{body}    return None\n"


def calls_source(count: int) -> str:
    """Build a function with the requested number of distinct calls."""

    helpers: str = "".join(
        f"def helper_{index}() -> int:\n    return {index}\n\n" for index in range(count)
    )
    calls: str = "".join(f"    value_{index}: int = helper_{index}()\n" for index in range(count))
    return f"{helpers}def run() -> None:\n{calls}    return None\n"


def locals_source(count: int) -> str:
    """Build a function with the requested number of assigned locals."""

    body: str = "".join(f"    value_{index}: int = {index}\n" for index in range(count))
    return f"def run() -> None:\n{body}    return None\n"


def _rule_by_code(rule_code: str) -> RuleSpec:
    for rule in SFS_RULES:
        if rule.code == rule_code:
            return rule
    raise AssertionError(f"Unknown SFS rule code {rule_code}")
