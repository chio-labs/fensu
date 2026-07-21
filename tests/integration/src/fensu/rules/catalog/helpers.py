"""Helpers for native core-rule Python boundary coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.config.models import Config
from fensu.discovery.main.discover_files import discover_files
from fensu.evaluation.main.evaluate import evaluate
from fensu.evaluation.models import EvaluationResult
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.catalog.constants import CORE_RULES
from tests.integration.src.fensu.rules.catalog._test_types import NativeCoreBoundaryTestCase

_CORE_RULES_BY_CODE: dict[str, RuleSpec] = {rule.code: rule for rule in CORE_RULES}


def evaluate_native_boundary(
    *,
    test_case: NativeCoreBoundaryTestCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[EvaluationResult, RuleSpec]:
    """Evaluate one native rule through Python discovery and fault conversion."""

    for relative_path, source in test_case.files:
        path: Path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    for root in (*test_case.roots, *test_case.tests, *test_case.tooling):
        (tmp_path / root).mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(
        roots=test_case.roots,
        tests=test_case.tests,
        tooling=test_case.tooling,
    )
    rule: RuleSpec = _CORE_RULES_BY_CODE[test_case.rule_code]
    return (
        evaluate(
            tree=discover_files(config=config),
            ruleset=(rule,),
            config=config,
        ),
        rule,
    )
