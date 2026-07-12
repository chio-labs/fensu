"""Helpers for layer rule tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.config.models import Config
from strata.discovery.main.discover_files import discover_files
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.models import EvaluationResult
from strata.rules.authoring.models import RuleSpec
from strata.rules.layers.constants import SFL_RULES
from tests.unit.src.strata.rules.layers.main._test_types import LayerRuleTestCase


def write_files(*, root: Path, files: tuple[tuple[str, str], ...]) -> None:
    """Write test fixture files."""

    for relative_path, source in files:
        path: Path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


def evaluate_layer_rule(
    *, rule_code: str, config: Config, monkeypatch: pytest.MonkeyPatch, repo_root: Path
) -> EvaluationResult:
    """Evaluate a single SFL rule over discovered fixture files."""

    monkeypatch.chdir(repo_root)
    return evaluate(
        tree=discover_files(config=config), ruleset=(_rule_by_code(rule_code),), config=config
    )


def evaluate_layer_test_case(
    *, test_case: LayerRuleTestCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> EvaluationResult:
    """Write files and evaluate a layer-rule test case."""

    write_files(root=tmp_path, files=test_case.files)
    config: Config = Config(roots=test_case.roots, tests=())
    return evaluate_layer_rule(
        rule_code=test_case.rule_code, config=config, monkeypatch=monkeypatch, repo_root=tmp_path
    )


def _rule_by_code(rule_code: str) -> RuleSpec:
    for rule in SFL_RULES:
        if rule.code == rule_code:
            return rule
    raise AssertionError(f"Unknown SFL rule code {rule_code}")
