"""Helpers for roles rule tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.config.core.models import Config
from strata.discovery.core.main.discover_files import discover_files
from strata.evaluation.core.main.evaluate import evaluate
from strata.evaluation.core.models import EvaluationResult
from strata.rules.authoring.models import RuleSpec
from strata.rules.roles.constants import SFR_RULES
from tests.unit.src.strata.rules.roles.main._test_types import SfrRuleTestCase


def evaluate_role_test_case(
    *, test_case: SfrRuleTestCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> EvaluationResult:
    """Write a source file and evaluate a single roles rule."""

    path: Path = tmp_path / "src" / "pkg" / test_case.relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(test_case.source, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",), tests=())
    return evaluate(
        tree=discover_files(config),
        ruleset=(_rule_by_code(test_case.rule_code),),
        config=config,
    )


def _rule_by_code(rule_code: str) -> RuleSpec:
    for rule in SFR_RULES:
        if rule.code == rule_code:
            return rule
    raise AssertionError(f"Unknown SFR rule code {rule_code}")
