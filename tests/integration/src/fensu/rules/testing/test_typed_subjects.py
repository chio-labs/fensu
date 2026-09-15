"""Integration tests for typed custom-rule subjects and project evaluation."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu import (
    ExecutionOwner,
    Family,
    Fault,
    File,
    Project,
    ProjectPath,
    RuleCase,
    RuleContext,
    RuleFile,
    RuleResult,
    SourceKind,
    evaluate_rule,
    rule,
)
from fensu.config.main.build_config import build_config
from fensu.discovery.main.discover_files import discover_files
from fensu.evaluation.exceptions import ProjectContextUnavailableError
from fensu.evaluation.main.evaluate import evaluate
from fensu.evaluation.models import EvaluationResult
from fensu.rules.authoring.constants import _RULE_SPEC_ATTRIBUTE
from fensu.rules.authoring.exceptions import RuleDefinitionError


@rule(
    code="XTS001",
    family=Family.CUSTOM,
    slug="typed-file-subject",
    message="typed file",
)
def typed_file_subject(*, subject: File, context: RuleContext) -> list[Fault]:
    """Report complete stable position facts supplied for each file identity."""

    position = context.project.tree.position(subject.path)
    assert position is not None
    assert position.path == subject.path
    assert position.analyzer.value == "python"
    assert position.source_kind is SourceKind.PYTHON_MODULE
    if subject.path.name == "check.py":
        assert position.scope_root == ProjectPath("src/example")
        assert position.module == "example.orders.fulfillment.main.internal.check"
        assert position.package == "example.orders.fulfillment.main.internal"
        assert position.domain_parts == ("orders", "fulfillment")
        assert position.role == "main"
        assert position.role_depth == 1
        assert position.is_entry_module
        assert position.is_main_module
    elif subject.path.name == "models.py":
        assert position.role == "models"
        assert position.role_depth == 0
    return [context.path_fault(message=f"{subject.path}:{position.role}")]


@rule(
    code="XTS002",
    family=Family.CUSTOM,
    slug="typed-project-subject",
    message="typed project",
)
def typed_project_subject(*, owner: Project, context: RuleContext) -> list[Fault]:
    """Report deterministic tree and requester-bound cross-file facts once."""

    del owner
    support = ProjectPath("tests/test_checkout.py")
    position = context.project.tree.position(support)
    assert position is not None
    assert context.project.exists(path=support)
    assert context.project.tree.children("tests") == (support,)
    assert support in context.project.tree.descendants()
    assert support in context.project.tree.glob("**/*.py")
    assert context.project.tree.files_under("tests") == (File(path=support),)
    return [
        context.path_fault(
            path=support,
            message=f"{len(context.project.tree.files)}:{position.scope.value}",
        )
    ]


@rule(
    code="XTS003",
    family=Family.CUSTOM,
    slug="anchor-free-project",
    message="anchor free",
)
def anchor_free_project(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Report without reading any current-file state."""

    del project
    return [ctx.path_fault(path="src/example/main/example.py")]


@rule(
    code="XTS004",
    family=Family.CUSTOM,
    slug="invalid-project-context-read",
    message="invalid project context read",
)
def invalid_project_context_read(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Exercise clear failure for current-file-only context state."""

    del project
    _ = ctx.source
    return []


@rule(
    code="XTS005",
    family=Family.CUSTOM,
    slug="invalid-project-glob",
    message="invalid project glob",
)
def invalid_project_glob(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Exercise confinement validation on tree glob inputs."""

    del project
    _ = ctx.project.tree.glob("../*.py")
    return []


@rule(
    code="XTS007",
    family=Family.CUSTOM,
    slug="invalid-project-tree-path",
    message="invalid project tree path",
)
def invalid_project_tree_path(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Exercise rejection of pathlib and absolute tree inputs."""

    del project
    _ = ctx.project.tree.position(Path("/outside.py"))  # ty: ignore[invalid-argument-type]
    return []


def test_given_discovered_sources_when_evaluating_file_subject_then_invokes_once_per_file() -> None:
    test_case = RuleCase(
        description="typed file invocation",
        source="value = 1\n",
        expected_fault_count=3,
        path="src/example/orders/fulfillment/main/internal/check.py",
        files=(
            RuleFile(path="src/example/inventory/models.py", source="value = 2\n"),
            RuleFile(path="tests/test_checkout.py", source="value = 3\n"),
        ),
    )

    result: RuleResult = evaluate_rule(rule=typed_file_subject, test_case=test_case)
    spec = getattr(typed_file_subject, _RULE_SPEC_ATTRIBUTE)

    assert result.fault_count == 3
    assert spec.subject_kind.value == "file"
    assert spec.subject_parameter == "subject"
    assert spec.context_parameter == "context"


def test_given_discovered_tree_when_evaluating_project_subject_then_invokes_exactly_once() -> None:
    test_case = RuleCase(
        description="typed project invocation",
        source="value = 1\n",
        expected_fault_count=1,
        path="src/example/orders/fulfillment/main/internal/check.py",
        files=(
            RuleFile(path="src/example/inventory/models.py", source="value = 2\n"),
            RuleFile(path="tests/test_checkout.py", source="value = 3\n"),
        ),
    )

    result: RuleResult = evaluate_rule(rule=typed_project_subject, test_case=test_case)

    assert result.fault_count == 1
    assert result.faults[0].path == Path("tests/test_checkout.py")
    assert result.faults[0].message == "3:test"
    assert len(result.dependencies) == 7
    assert {dependency.requester for dependency in result.dependencies} == {
        Path(".fensu-project-rule")
    }
    assert {dependency.kind for dependency in result.dependencies} >= {
        "tree_children",
        "tree_descendants",
        "tree_files",
        "tree_files_under",
        "tree_glob",
        "tree_position",
    }


def test_given_no_discovered_files_when_evaluating_project_rule_then_runs_without_anchor(
    tmp_path: Path,
) -> None:
    (tmp_path / "src/example").mkdir(parents=True)
    config = build_config(raw={"roots": ["src/example"], "tests": [], "tooling": []})
    tree = discover_files(config=config, repo_root=tmp_path)

    result: EvaluationResult = evaluate(
        tree=tree,
        ruleset=(getattr(anchor_free_project, _RULE_SPEC_ATTRIBUTE),),
        config=config,
    )

    assert tree.files == ()
    assert len(result.faults) == 1
    assert result.faults[0].path == tmp_path / "src/example/main/example.py"


@pytest.mark.parametrize(
    "value",
    ("/etc/passwd", "../outside.py", "folder\\file.py", "C:/folder/file.py", "a/../b.py"),
)
def test_given_unconfined_path_when_constructing_project_path_then_rejects(value: str) -> None:
    with pytest.raises(ValueError, match="project-relative POSIX path"):
        ProjectPath(value)


def test_given_unconfined_glob_when_querying_tree_then_rejects() -> None:
    test_case = RuleCase(
        description="invalid glob",
        source="value = 1\n",
        expected_fault_count=1,
    )

    with pytest.raises(ValueError, match="confined project-relative POSIX pattern"):
        evaluate_rule(rule=invalid_project_glob, test_case=test_case)


def test_given_pathlib_path_when_querying_tree_then_rejects() -> None:
    test_case = RuleCase(
        description="invalid tree path type",
        source="value = 1\n",
        expected_fault_count=0,
    )

    with pytest.raises(TypeError, match="ProjectPath or str"):
        evaluate_rule(rule=invalid_project_tree_path, test_case=test_case)


def test_given_project_warning_rule_when_evaluating_then_reports_warning_once(
    tmp_path: Path,
) -> None:
    (tmp_path / "src/example").mkdir(parents=True)
    config = build_config(raw={"roots": ["src/example"], "tests": [], "tooling": []})
    tree = discover_files(config=config, repo_root=tmp_path)

    result = evaluate(
        tree=tree,
        ruleset=(),
        warning_rules=(getattr(anchor_free_project, _RULE_SPEC_ATTRIBUTE),),
        config=config,
    )

    assert result.faults == ()
    assert len(result.warnings) == 1


def test_given_project_file_exception_when_evaluating_then_suppresses_project_fault() -> None:
    test_case = RuleCase(
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
    )

    result = evaluate_rule(rule=anchor_free_project, test_case=test_case)

    assert result.fault_count == 0


def test_given_project_rule_when_reading_file_context_then_fails_clearly() -> None:
    test_case = RuleCase(
        description="project context failure",
        source="value = 1\n",
        expected_fault_count=0,
    )

    with pytest.raises(ProjectContextUnavailableError, match="no current file"):
        evaluate_rule(rule=invalid_project_context_read, test_case=test_case)


def test_given_conflicting_explicit_owner_when_defining_typed_rule_then_rejects() -> None:
    with pytest.raises(RuleDefinitionError, match="conflicts with explicit execution_owner"):

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
