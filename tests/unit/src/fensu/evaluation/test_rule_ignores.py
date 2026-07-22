"""Tests for additive selector-and-reported-path finding suppression."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.config.models import Config, RuleExceptionEntry, RuleIgnoreEntry
from fensu.evaluation._helpers.collection import collect_evaluation_result
from fensu.evaluation.models import EvaluationResult, FileEvaluation, RuleExceptionKey
from fensu.rules.authoring.models import Fault
from tests.unit.src.fensu.evaluation._test_types import RuleIgnoreCollectionTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        RuleIgnoreCollectionTestCase(
            description="one declaration must match both selector and reported path",
            expected_faults=(
                ("FFS001", "src/pkg/generated.py"),
                ("FFA001", "src/pkg/live.py"),
            ),
            expected_warnings=(("FFA001", "src/pkg/live.py"),),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_rule_and_path_conjunction_when_collecting_then_filters_blocking_and_warning_findings(
    tmp_path: Path,
    test_case: RuleIgnoreCollectionTestCase,
) -> None:
    generated: Path = tmp_path / "src/pkg/generated.py"
    live: Path = tmp_path / "src/pkg/live.py"
    file_evaluation: FileEvaluation = FileEvaluation(
        path=live,
        source_fingerprint="source",
        faults=(
            Fault(code="FFA001", path=generated, message="ignored"),
            Fault(code="FFA001", path=live, message="retained path"),
            Fault(code="FFS001", path=generated, message="retained rule"),
        ),
        warnings=(
            Fault(code="FFA001", path=generated, message="ignored warning"),
            Fault(code="FFA001", path=live, message="retained warning"),
        ),
        applied_exception_keys=(),
        dependencies=(),
    )
    config: Config = Config(
        roots=("src/pkg",),
        rule_ignores=(
            RuleIgnoreEntry(
                rules=("FFA",),
                paths=("src/pkg/generated.py",),
                reason="Generated interfaces are checked upstream.",
            ),
        ),
    )

    result: EvaluationResult = collect_evaluation_result(
        file_evaluations=(file_evaluation,),
        dependencies=(),
        config=config,
        repo_root=tmp_path,
    )

    assert (
        tuple((fault.code, fault.path.relative_to(tmp_path).as_posix()) for fault in result.faults)
        == test_case.expected_faults
    )
    assert (
        tuple(
            (fault.code, fault.path.relative_to(tmp_path).as_posix()) for fault in result.warnings
        )
        == test_case.expected_warnings
    )


@pytest.mark.parametrize(
    "test_case",
    [
        RuleIgnoreCollectionTestCase(
            description="exact exception remains applied before overlapping broad policy",
            expected_faults=(),
            expected_warnings=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_exact_exception_and_rule_ignore_when_collecting_then_exact_exception_is_not_stale(
    tmp_path: Path,
    test_case: RuleIgnoreCollectionTestCase,
) -> None:
    relative_path: str = "src/pkg/generated.py"
    key: RuleExceptionKey = RuleExceptionKey(rule="FFA001", path=relative_path, symbol=None)
    file_evaluation: FileEvaluation = FileEvaluation(
        path=tmp_path / relative_path,
        source_fingerprint="source",
        faults=(),
        warnings=(),
        applied_exception_keys=(key,),
        dependencies=(),
    )
    config: Config = Config(
        roots=("src/pkg",),
        rule_exceptions=(
            RuleExceptionEntry(rule="FFA001", path=relative_path, reason="Exact adapter."),
        ),
        rule_ignores=(
            RuleIgnoreEntry(
                rules=("FFA",),
                paths=("src/pkg/generated.py",),
                reason="Generated interfaces are checked upstream.",
            ),
        ),
    )

    result: EvaluationResult = collect_evaluation_result(
        file_evaluations=(file_evaluation,),
        dependencies=(),
        config=config,
        repo_root=tmp_path,
    )

    assert result.faults == test_case.expected_faults
    assert result.warnings == test_case.expected_warnings
    assert result.applied_exception_count == 1
