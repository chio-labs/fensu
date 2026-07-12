"""Helpers for roles rule tests."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from strata.config.core.constants import DEFAULT_THRESHOLDS
from strata.config.core.models import Config
from strata.discovery.core.main.discover_files import discover_files
from strata.evaluation.core.main.evaluate import evaluate
from strata.evaluation.core.models import EvaluationResult
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Threshold
from strata.rules.roles.constants import SFR_RULES
from tests.unit.src.strata.rules.roles.main._test_types import SfrRuleTestCase


def evaluate_role_test_case(
    *, test_case: SfrRuleTestCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> EvaluationResult:
    """Write a source file and evaluate a single roles rule."""

    scope_root: Path = tmp_path / ("scripts" if test_case.scope == "tooling" else "src/pkg")
    path: Path = scope_root / test_case.relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(test_case.source, encoding="utf-8")
    for support_file in test_case.support_files:
        support_path: Path = scope_root / support_file.relative_path
        support_path.parent.mkdir(parents=True, exist_ok=True)
        support_path.write_text(support_file.source, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    thresholds: dict[Threshold, int] = dict(DEFAULT_THRESHOLDS)
    thresholds.update(test_case.thresholds)
    runtime_root: Path = tmp_path / "src/pkg"
    runtime_root.mkdir(parents=True, exist_ok=True)
    tooling: tuple[str, ...] = ("scripts",) if test_case.scope == "tooling" else ()
    config: Config = Config(
        roots=("src/pkg",),
        tests=(),
        tooling=tooling,
        thresholds=MappingProxyType(thresholds),
    )
    return evaluate(
        tree=discover_files(config=config),
        ruleset=(_rule_by_code(test_case.rule_code),),
        config=config,
    )


def _rule_by_code(rule_code: str) -> RuleSpec:
    for rule in SFR_RULES:
        if rule.code == rule_code:
            return rule
    raise AssertionError(f"Unknown SFR rule code {rule_code}")
