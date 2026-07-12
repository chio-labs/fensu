"""Tests for the uncached one-file evaluation boundary."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from strata.config.core.models import Config, RuleExceptionEntry
from strata.discovery.core.models import DiscoveredTree, ScopedFile
from strata.evaluation.core.helpers.file_evaluation import evaluate_file
from strata.evaluation.core.helpers.project_analysis import build_project_analysis
from strata.evaluation.core.models import FileEvaluation
from strata.evaluation.core.types import EvaluationProjectAnalysis
from tests.unit.src.strata.evaluation.core._test_types import (
    FileEvaluationExceptionTestCase,
    FileEvaluationTestCase,
)
from tests.unit.src.strata.evaluation.core.helpers import (
    discover_test_tree,
    make_project_dependency_rule,
    make_static_fault_rule,
    write_sources,
)


@pytest.mark.parametrize(
    "test_case",
    [
        FileEvaluationTestCase(
            description="file boundary returns source faults and requester observations",
            file_path="src/pkg/config/core/models.py",
            source="value: int = 1\n",
            expected_fault_codes=("XEV001",),
            expected_dependency_answers=(False,),
            expected_applied_exception_keys=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_discovered_file_when_evaluating_then_returns_complete_file_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FileEvaluationTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=((test_case.file_path, test_case.source),))
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))
    tree: DiscoveredTree = discover_test_tree(config=config)
    scoped_file: ScopedFile = tree.files[0]
    project: EvaluationProjectAnalysis = build_project_analysis(tree=tree)

    result: FileEvaluation = evaluate_file(
        scoped_file=scoped_file,
        ruleset=(
            make_static_fault_rule(code="XEV001", line=1, message="file fault"),
            make_project_dependency_rule(),
        ),
        config=config,
        tree=tree,
        project=project,
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_fault_codes
    assert (
        tuple(item.answer for item in result.dependencies) == test_case.expected_dependency_answers
    )
    assert len(result.applied_exception_keys) == test_case.expected_applied_exception_keys
    assert result.path == scoped_file.path
    assert result.source_fingerprint == hashlib.sha256(test_case.source.encode("utf-8")).hexdigest()
    assert all(item.requester == scoped_file.path.resolve() for item in result.dependencies)


@pytest.mark.parametrize(
    "test_case",
    [
        FileEvaluationExceptionTestCase(
            description="file boundary retains exact applied exception keys",
            file_path="src/pkg/config/core/models.py",
            source="def build() -> None:\n    value = 1\n",
            expected_fault_count=0,
            expected_applied_symbols=("build",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_matching_exception_when_evaluating_file_then_returns_applied_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FileEvaluationExceptionTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=((test_case.file_path, test_case.source),))
    monkeypatch.chdir(tmp_path)
    config: Config = Config(
        roots=("src/pkg",),
        rule_exceptions=(
            RuleExceptionEntry(
                rule="XEV001",
                path=test_case.file_path,
                symbols=("build",),
                reason="covered by file boundary",
            ),
        ),
    )
    tree: DiscoveredTree = discover_test_tree(config=config)
    scoped_file: ScopedFile = tree.files[0]
    project: EvaluationProjectAnalysis = build_project_analysis(tree=tree)

    result: FileEvaluation = evaluate_file(
        scoped_file=scoped_file,
        ruleset=(make_static_fault_rule(code="XEV001", line=2, message="file fault"),),
        config=config,
        tree=tree,
        project=project,
    )

    assert len(result.faults) == test_case.expected_fault_count
    assert tuple(key.symbol for key in result.applied_exception_keys) == (
        test_case.expected_applied_symbols
    )
