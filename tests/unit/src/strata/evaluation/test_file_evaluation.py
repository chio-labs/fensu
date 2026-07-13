"""Tests for the uncached one-file evaluation boundary."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from strata.config.models import Config, RuleExceptionEntry
from strata.discovery.models import DiscoveredTree, ScopedFile
from strata.evaluation._helpers.file_evaluation import evaluate_file
from strata.evaluation._helpers.project_analysis import build_project_analysis
from strata.evaluation.models import FileEvaluation
from strata.evaluation.types import EvaluationProjectAnalysis
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family
from strata.rules.catalog._helpers import loading as loading_module
from strata.rules.catalog.main.build_ruleset import build_ruleset
from tests.unit.src.strata.evaluation._test_types import (
    FileEvaluationExceptionTestCase,
    FileEvaluationTestCase,
    ScopeFamilySelectionTestCase,
)
from tests.unit.src.strata.evaluation.helpers import (
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


@pytest.mark.parametrize(
    "test_case",
    [
        ScopeFamilySelectionTestCase(
            description="X selects custom code while tests family limits execution to test scope",
            runtime_path="src/pkg/runtime.py",
            test_path="tests/test_runtime.py",
            expected_selected_codes=("XSC001",),
            expected_fault_paths=("tests/test_runtime.py",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_custom_code_with_tests_family_when_selecting_x_then_executes_only_test_scope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ScopeFamilySelectionTestCase,
) -> None:
    write_sources(
        repo_root=tmp_path,
        files=((test_case.runtime_path, "value = 1\n"), (test_case.test_path, "value = 1\n")),
    )
    monkeypatch.chdir(tmp_path)
    custom_rule: RuleSpec = make_static_fault_rule(
        code="XSC001",
        line=1,
        message="scope fault",
        family=Family.TESTS,
    )
    monkeypatch.setattr(loading_module, "CORE_RULES", (custom_rule,))
    config: Config = Config(roots=("src/pkg",), tests=("tests",), select=("X",))
    tree: DiscoveredTree = discover_test_tree(config=config)
    project: EvaluationProjectAnalysis = build_project_analysis(tree=tree)
    ruleset: tuple[RuleSpec, ...] = build_ruleset(config=config, repo_root=tmp_path)
    results: tuple[FileEvaluation, ...] = tuple(
        evaluate_file(
            scoped_file=scoped_file,
            ruleset=ruleset,
            config=config,
            tree=tree,
            project=project,
        )
        for scoped_file in tree.files
    )
    fault_paths: list[str] = []
    for result in results:
        for fault in result.faults:
            fault_paths.append(fault.path.relative_to(tmp_path).as_posix())

    assert tuple(rule.code for rule in ruleset) == test_case.expected_selected_codes
    assert tuple(fault_paths) == test_case.expected_fault_paths
