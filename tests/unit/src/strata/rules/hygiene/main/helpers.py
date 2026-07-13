"""Helpers for hygiene rule tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.config.models import Config
from strata.discovery.main.discover_files import discover_files
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.models import EvaluationResult
from strata.rules.authoring.models import RuleSpec
from strata.rules.hygiene.constants import SFH_RULES
from tests.unit.src.strata.rules.hygiene.main._test_types import HygieneRuleTestCase


def evaluate_hygiene_test_case(
    *, test_case: HygieneRuleTestCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> EvaluationResult:
    """Write a source file and evaluate a single hygiene rule."""

    path: Path = tmp_path / test_case.relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(test_case.source, encoding="utf-8")
    for root in test_case.roots:
        (tmp_path / root).mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(
        roots=test_case.roots,
        tests=test_case.tests,
        tooling=test_case.tooling,
    )
    return evaluate(
        tree=discover_files(config=config),
        ruleset=(_rule_by_code(test_case.rule_code),),
        config=config,
    )


def _rule_by_code(rule_code: str) -> RuleSpec:
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in SFH_RULES}
    return rules_by_code[rule_code]
