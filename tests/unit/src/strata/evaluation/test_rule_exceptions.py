"""Tests for exact symbol-scoped rule exception evaluation."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.config.exceptions import ConfigError
from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.main.validate_rule_exceptions import validate_rule_exceptions
from strata.evaluation.models import EvaluationResult
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.main.build_ruleset import build_ruleset
from tests.unit.src.strata.evaluation._test_types import (
    RuleExceptionEvaluationTestCase,
    RuleExceptionTargetTestCase,
)
from tests.unit.src.strata.evaluation.helpers import (
    discover_test_tree,
    make_rule_exception_config,
    write_exception_target,
    write_sources,
)

_source_path: str = "src/pkg/integrations/helpers/progress.py"
_reason: str = "External callbacks invoke these symbols positionally."


@pytest.mark.parametrize(
    "test_case",
    [
        RuleExceptionEvaluationTestCase(
            description="methods and nested functions resolve to exact innermost owners",
            source=(
                "class Collector:\n"
                "    def update(self, value: int) -> None:\n"
                "        pass\n"
                "def outer() -> None:\n"
                "    def nested(value: int) -> None:\n"
                "        pass\n"
            ),
            symbols=("Collector.update", "outer.nested"),
            expected_fault_lines=(),
            expected_applied_exception_count=2,
            expected_error_fragment=None,
        ),
        RuleExceptionEvaluationTestCase(
            description="exception leaves a fault owned by another symbol",
            source=(
                "def exempt(value: int) -> None:\n"
                "    pass\n"
                "def retained(value: int) -> None:\n"
                "    pass\n"
            ),
            symbols=("exempt",),
            expected_fault_lines=(3,),
            expected_applied_exception_count=1,
            expected_error_fragment=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_exact_rule_exceptions_when_evaluating_then_suppresses_only_matching_symbols(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: RuleExceptionEvaluationTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=((_source_path, test_case.source),))
    monkeypatch.chdir(tmp_path)
    config: Config = make_rule_exception_config(
        path=_source_path, symbols=test_case.symbols, reason=_reason
    )
    tree: DiscoveredTree = discover_test_tree(config=config)
    ruleset: tuple[RuleSpec, ...] = build_ruleset(config=config)
    validate_rule_exceptions(config=config, repo_root=tree.repo_root.path)

    result: EvaluationResult = evaluate(tree=tree, ruleset=ruleset, config=config)

    assert tuple(fault.line for fault in result.faults) == test_case.expected_fault_lines
    assert result.applied_exception_count == test_case.expected_applied_exception_count


@pytest.mark.parametrize(
    "test_case",
    [
        RuleExceptionEvaluationTestCase(
            description="resolved exception that suppresses no fault is stale",
            source="def run(*, value: int) -> None:\n    pass\n",
            symbols=("run",),
            expected_fault_lines=(),
            expected_applied_exception_count=0,
            expected_error_fragment="Stale rule exception",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_inactive_rule_exception_when_evaluating_then_raises_stale_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: RuleExceptionEvaluationTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=((_source_path, test_case.source),))
    monkeypatch.chdir(tmp_path)
    config: Config = make_rule_exception_config(
        path=_source_path, symbols=test_case.symbols, reason=_reason
    )
    tree: DiscoveredTree = discover_test_tree(config=config)
    validate_rule_exceptions(config=config, repo_root=tree.repo_root.path)

    with pytest.raises(ConfigError) as error:
        evaluate(tree=tree, ruleset=build_ruleset(config=config), config=config)

    assert test_case.expected_error_fragment is not None
    assert test_case.expected_error_fragment in str(error.value)
    assert test_case.symbols[0] in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        RuleExceptionTargetTestCase(
            description="nonexistent exception path is rejected",
            path=_source_path,
            symbol="run",
            create_path=False,
            expected_error_fragment="does not exist",
        ),
        RuleExceptionTargetTestCase(
            description="unresolved exception symbol is rejected",
            path=_source_path,
            symbol="missing",
            create_path=True,
            expected_error_fragment="does not exist",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_exception_target_when_validating_then_raises_config_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: RuleExceptionTargetTestCase,
) -> None:
    write_exception_target(
        repo_root=tmp_path,
        path=test_case.path,
        create_path=test_case.create_path,
    )
    monkeypatch.chdir(tmp_path)
    config: Config = make_rule_exception_config(
        path=test_case.path, symbols=(test_case.symbol,), reason=_reason
    )

    with pytest.raises(ConfigError) as error:
        validate_rule_exceptions(config=config, repo_root=tmp_path)

    assert test_case.expected_error_fragment in str(error.value)
