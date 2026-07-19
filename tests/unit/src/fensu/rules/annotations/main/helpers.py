"""Helpers for annotation rule tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.config.models import Config
from fensu.discovery.main.discover_files import discover_files
from fensu.evaluation.main.evaluate import evaluate
from fensu.evaluation.models import EvaluationResult
from fensu.rules.annotations.constants import FFA_RULES
from fensu.rules.authoring.models import RuleSpec
from tests.unit.src.fensu.rules.annotations.main._test_types import AnnotationRuleTestCase


def evaluate_annotation_test_case(
    *, test_case: AnnotationRuleTestCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> EvaluationResult:
    """Write a source file and evaluate a single annotation rule."""

    path: Path = tmp_path / "src" / "pkg" / "domain" / "core" / "models.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(test_case.source, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",), tests=())
    return evaluate(
        tree=discover_files(config=config),
        ruleset=(_rule_by_code(test_case.rule_code),),
        config=config,
    )


def _rule_by_code(rule_code: str) -> RuleSpec:
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in FFA_RULES}
    return rules_by_code[rule_code]
