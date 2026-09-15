"""Integration tests for typed custom-rule subjects and project evaluation."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu import (
    ExecutionOwner,
    Family,
    Fault,
    File,
    ProjectPath,
    RuleCase,
    RuleContext,
    RuleFile,
    RuleResult,
    evaluate_rule,
    rule,
)
from fensu.config.main.build_config import build_config
from fensu.config.models import Config
from fensu.discovery.main.discover_files import discover_files
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation.exceptions import ProjectContextUnavailableError
from fensu.evaluation.main.evaluate import evaluate
from fensu.evaluation.models import EvaluationResult
from fensu.rules.authoring.constants import _RULE_SPEC_ATTRIBUTE
from fensu.rules.authoring.exceptions import RuleDefinitionError
from fensu.rules.authoring.models import RuleSpec
from tests.integration.src.fensu.rules.testing._test_types import (
    ConflictingOwnerTestCase,
    EmptyProjectSubjectTestCase,
    InvalidProjectPathTestCase,
    ProjectExceptionTestCase,
    ProjectWarningTestCase,
    TypedFileSubjectTestCase,
    TypedProjectSubjectTestCase,
    TypedRuleFailureTestCase,
)
from tests.integration.src.fensu.rules.testing.helpers import (
    anchor_free_project,
    invalid_project_context_read,
    invalid_project_glob,
    invalid_project_tree_path,
    typed_file_subject,
    typed_project_subject,
)


@pytest.mark.parametrize(
    "test_case",
    [
        TypedFileSubjectTestCase(
            description="typed file rule runs once for each discovered source",
            rule_case=RuleCase(
                description="typed file invocation",
                source="value = 1\n",
                expected_fault_count=3,
                path="src/example/orders/fulfillment/main/internal/check.py",
                files=(
                    RuleFile(path="src/example/inventory/models.py", source="value = 2\n"),
                    RuleFile(path="tests/test_checkout.py", source="value = 3\n"),
                ),
            ),
            expected_fault_count=3,
            expected_subject_kind="file",
            expected_subject_parameter="subject",
            expected_context_parameter="context",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_discovered_sources_when_evaluating_file_subject_then_invokes_once_per_file(
    test_case: TypedFileSubjectTestCase,
) -> None:
    result: RuleResult = evaluate_rule(rule=typed_file_subject, test_case=test_case.rule_case)
    spec: RuleSpec = getattr(typed_file_subject, _RULE_SPEC_ATTRIBUTE)

    assert result.fault_count == test_case.expected_fault_count
    assert spec.subject_kind.value == test_case.expected_subject_kind
    assert spec.subject_parameter == test_case.expected_subject_parameter
    assert spec.context_parameter == test_case.expected_context_parameter


@pytest.mark.parametrize(
    "test_case",
    [
        TypedProjectSubjectTestCase(
            description="typed project rule runs once for the discovered tree",
            rule_case=RuleCase(
                description="typed project invocation",
                source="value = 1\n",
                expected_fault_count=1,
                path="src/example/orders/fulfillment/main/internal/check.py",
                files=(
                    RuleFile(path="src/example/inventory/models.py", source="value = 2\n"),
                    RuleFile(path="tests/test_checkout.py", source="value = 3\n"),
                ),
            ),
            expected_fault_count=1,
            expected_path=Path("tests/test_checkout.py"),
            expected_message="3:test",
            expected_dependency_count=7,
            expected_requesters=frozenset({Path(".fensu-project-rule")}),
            expected_dependency_kinds=frozenset(
                {
                    "tree_children",
                    "tree_descendants",
                    "tree_files",
                    "tree_files_under",
                    "tree_glob",
                    "tree_position",
                }
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_discovered_tree_when_evaluating_project_subject_then_invokes_exactly_once(
    test_case: TypedProjectSubjectTestCase,
) -> None:
    result: RuleResult = evaluate_rule(rule=typed_project_subject, test_case=test_case.rule_case)

    assert result.fault_count == test_case.expected_fault_count
    assert result.faults[0].path == test_case.expected_path
    assert result.faults[0].message == test_case.expected_message
    assert len(result.dependencies) == test_case.expected_dependency_count
    assert {
        dependency.requester for dependency in result.dependencies
    } == test_case.expected_requesters
    assert {
        dependency.kind for dependency in result.dependencies
    } >= test_case.expected_dependency_kinds


@pytest.mark.parametrize(
    "test_case",
    [
        EmptyProjectSubjectTestCase(
            description="project rule runs without a discovered file anchor",
            expected_file_count=0,
            expected_fault_count=1,
            expected_fault_path="src/example/main/example.py",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_discovered_files_when_evaluating_project_rule_then_runs_without_anchor(
    tmp_path: Path,
    test_case: EmptyProjectSubjectTestCase,
) -> None:
    (tmp_path / "src/example").mkdir(parents=True)
    config: Config = build_config(raw={"roots": ["src/example"], "tests": [], "tooling": []})
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)

    result: EvaluationResult = evaluate(
        tree=tree,
        ruleset=(getattr(anchor_free_project, _RULE_SPEC_ATTRIBUTE),),
        config=config,
    )

    assert len(tree.files) == test_case.expected_file_count
    assert len(result.faults) == test_case.expected_fault_count
    assert result.faults[0].path == tmp_path / test_case.expected_fault_path


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidProjectPathTestCase(
            description="absolute POSIX path",
            value="/etc/passwd",
            expected_error_fragment="project-relative POSIX path",
        ),
        InvalidProjectPathTestCase(
            description="parent traversal",
            value="../outside.py",
            expected_error_fragment="project-relative POSIX path",
        ),
        InvalidProjectPathTestCase(
            description="backslash separator",
            value="folder\\file.py",
            expected_error_fragment="project-relative POSIX path",
        ),
        InvalidProjectPathTestCase(
            description="Windows drive path",
            value="C:/folder/file.py",
            expected_error_fragment="project-relative POSIX path",
        ),
        InvalidProjectPathTestCase(
            description="embedded parent traversal",
            value="a/../b.py",
            expected_error_fragment="project-relative POSIX path",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_unconfined_path_when_constructing_project_path_then_rejects(
    test_case: InvalidProjectPathTestCase,
) -> None:
    with pytest.raises(ValueError, match=test_case.expected_error_fragment):
        ProjectPath(test_case.value)


@pytest.mark.parametrize(
    "test_case",
    [
        TypedRuleFailureTestCase(
            description="unconfined project glob is rejected",
            rule_case=RuleCase(
                description="invalid glob",
                source="value = 1\n",
                expected_fault_count=1,
            ),
            expected_error_type=ValueError,
            expected_error_fragment="confined project-relative POSIX pattern",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unconfined_glob_when_querying_tree_then_rejects(
    test_case: TypedRuleFailureTestCase,
) -> None:
    with pytest.raises(test_case.expected_error_type, match=test_case.expected_error_fragment):
        evaluate_rule(rule=invalid_project_glob, test_case=test_case.rule_case)


@pytest.mark.parametrize(
    "test_case",
    [
        TypedRuleFailureTestCase(
            description="pathlib project tree query is rejected",
            rule_case=RuleCase(
                description="invalid tree path type",
                source="value = 1\n",
                expected_fault_count=0,
            ),
            expected_error_type=TypeError,
            expected_error_fragment="ProjectPath or str",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_pathlib_path_when_querying_tree_then_rejects(
    test_case: TypedRuleFailureTestCase,
) -> None:
    with pytest.raises(test_case.expected_error_type, match=test_case.expected_error_fragment):
        evaluate_rule(rule=invalid_project_tree_path, test_case=test_case.rule_case)


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectWarningTestCase(
            description="project warning is reported once without files",
            expected_fault_count=0,
            expected_warning_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_warning_rule_when_evaluating_then_reports_warning_once(
    tmp_path: Path,
    test_case: ProjectWarningTestCase,
) -> None:
    (tmp_path / "src/example").mkdir(parents=True)
    config: Config = build_config(raw={"roots": ["src/example"], "tests": [], "tooling": []})
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)

    result: EvaluationResult = evaluate(
        tree=tree,
        ruleset=(),
        warning_rules=(getattr(anchor_free_project, _RULE_SPEC_ATTRIBUTE),),
        config=config,
    )

    assert len(result.faults) == test_case.expected_fault_count
    assert len(result.warnings) == test_case.expected_warning_count


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectExceptionTestCase(
            description="project path exception suppresses its fault",
            rule_case=RuleCase(
                description="project file exception",
                source="value = 1\n",
                expected_fault_count=0,
                config={
                    "rule_exceptions": [
                        {
                            "rule": "XTS003",
                            "path": "src/example/main/example.py",
                            "reason": "Neutral project exception fixture.",
                        }
                    ]
                },
            ),
            expected_fault_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_file_exception_when_evaluating_then_suppresses_project_fault(
    test_case: ProjectExceptionTestCase,
) -> None:
    result: RuleResult = evaluate_rule(rule=anchor_free_project, test_case=test_case.rule_case)

    assert result.fault_count == test_case.expected_fault_count


@pytest.mark.parametrize(
    "test_case",
    [
        TypedRuleFailureTestCase(
            description="project rule cannot read current file context",
            rule_case=RuleCase(
                description="project context failure",
                source="value = 1\n",
                expected_fault_count=0,
            ),
            expected_error_type=ProjectContextUnavailableError,
            expected_error_fragment="no current file",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_rule_when_reading_file_context_then_fails_clearly(
    test_case: TypedRuleFailureTestCase,
) -> None:
    with pytest.raises(test_case.expected_error_type, match=test_case.expected_error_fragment):
        evaluate_rule(rule=invalid_project_context_read, test_case=test_case.rule_case)


@pytest.mark.parametrize(
    "test_case",
    [
        ConflictingOwnerTestCase(
            description="typed file subject conflicts with explicit project owner",
            expected_error_fragment="conflicts with explicit execution_owner",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_conflicting_explicit_owner_when_defining_typed_rule_then_rejects(
    test_case: ConflictingOwnerTestCase,
) -> None:
    with pytest.raises(RuleDefinitionError, match=test_case.expected_error_fragment):

        @rule(
            code="XTS006",
            family=Family.CUSTOM,
            slug="conflicting-owner",
            message="conflicting owner",
            execution_owner=ExecutionOwner.PROJECT,
        )
        def conflicting_owner(*, file: File, ctx: RuleContext) -> list[Fault]:
            del file, ctx
            return []


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
