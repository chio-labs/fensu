"""Tests for evaluation-scoped project analysis behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.analysis.core.models import ProjectDependency, ProjectFunctionFact
from strata.analysis.core.types import Analysis
from strata.discovery.core.models import DiscoveredTree, RepoRoot, ScopedFile
from strata.discovery.core.types import ScopeName
from strata.evaluation.core.exceptions import ParseError
from strata.evaluation.core.helpers.parsing import parse_scoped_file
from strata.evaluation.core.helpers.project_analysis import build_project_analysis
from strata.evaluation.core.models import ParsedModule
from strata.evaluation.core.types import EvaluationProjectAnalysis
from tests.unit.src.strata.evaluation.core._test_types import (
    ProjectDependencyTestCase,
    ProjectDirectoryQueryTestCase,
    ProjectParseContractTestCase,
    ProjectRetentionTestCase,
)
from tests.unit.src.strata.evaluation.core.helpers import exercise_project_parse_order


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectDependencyTestCase(
            description="missing module records every precedence candidate",
            module_name="pkg.phases",
            expected_dependency_paths=(
                "src/pkg/phases.py",
                "src/pkg/phases/__init__.py",
                "pkg/phases.py",
                "pkg/phases/__init__.py",
            ),
            expected_dependency_kinds=("is_file", "is_file", "is_file", "is_file"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_missing_module_when_querying_then_records_all_candidate_dependencies(
    tmp_path: Path,
    test_case: ProjectDependencyTestCase,
) -> None:
    requester: Path = tmp_path / "src/pkg/main/run.py"
    project: EvaluationProjectAnalysis = build_project_analysis(
        tree=DiscoveredTree(files=(), repo_root=RepoRoot(tmp_path))
    )

    function: ProjectFunctionFact | None = project.module_function(
        requester=requester,
        module_name=test_case.module_name,
        function_name="run",
    )
    dependencies: tuple[ProjectDependency, ...] = project.dependencies()

    assert function is None
    assert tuple(item.requester for item in dependencies) == (requester.resolve(),) * len(
        test_case.expected_dependency_paths
    )
    assert tuple(str(item.dependency.relative_to(tmp_path)) for item in dependencies) == (
        test_case.expected_dependency_paths
    )
    assert tuple(item.kind for item in dependencies) == test_case.expected_dependency_kinds


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectDirectoryQueryTestCase(
            description="directory queries record listing and glob namespace inputs",
            expected_entry_names=("direct.py", "nested", "notes.txt"),
            expected_direct_matches=("direct.py",),
            expected_recursive_matches=("direct.py", "nested/nested.py"),
            expected_dependency_kinds=("directory_entries", "glob", "glob", "glob"),
            expected_patterns=(None, "*.py", "*.py", "*.sql"),
            expected_recursive=(False, False, True, True),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_directory_queries_when_observing_then_records_aggregate_dependencies(
    tmp_path: Path,
    test_case: ProjectDirectoryQueryTestCase,
) -> None:
    package: Path = tmp_path / "src/pkg/domain"
    nested: Path = package / "nested"
    nested.mkdir(parents=True)
    (package / "direct.py").write_text("", encoding="utf-8")
    (package / "notes.txt").write_text("", encoding="utf-8")
    (nested / "nested.py").write_text("", encoding="utf-8")
    requester: Path = tmp_path / "src/pkg/main/run.py"
    project: EvaluationProjectAnalysis = build_project_analysis(
        tree=DiscoveredTree(files=(), repo_root=RepoRoot(tmp_path))
    )

    entries: tuple[Path, ...] = project.directory_entries(requester=requester, path=package)
    repeated_entries: tuple[Path, ...] = project.directory_entries(
        requester=requester,
        path=package,
    )
    direct_matches: tuple[Path, ...] = project.glob(
        requester=requester,
        path=package,
        pattern="*.py",
    )
    recursive_matches: tuple[Path, ...] = project.glob(
        requester=requester,
        path=package,
        pattern="*.py",
        recursive=True,
    )
    no_matches: tuple[Path, ...] = project.glob(
        requester=requester,
        path=package,
        pattern="*.sql",
        recursive=True,
    )
    dependencies: tuple[ProjectDependency, ...] = project.dependencies()

    assert tuple(sorted(path.name for path in entries)) == test_case.expected_entry_names
    assert repeated_entries == entries
    assert tuple(path.name for path in direct_matches) == test_case.expected_direct_matches
    assert (
        tuple(str(path.relative_to(package)) for path in recursive_matches)
        == test_case.expected_recursive_matches
    )
    assert no_matches == ()
    assert tuple(item.kind for item in dependencies) == test_case.expected_dependency_kinds
    assert tuple(item.pattern for item in dependencies) == test_case.expected_patterns
    assert tuple(item.recursive for item in dependencies) == test_case.expected_recursive
    assert all(item.query_path == package for item in dependencies)
    assert all(item.dependency == package.resolve() for item in dependencies)


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectRetentionTestCase(
            description="queried ordinary file is reused at its normal turn",
            file_name="phase.py",
            query_first=True,
            expected_parse_count=1,
        ),
        ProjectRetentionTestCase(
            description="ordinary file queried after its turn is reparsed tolerantly",
            file_name="phase.py",
            query_first=False,
            expected_parse_count=2,
        ),
        ProjectRetentionTestCase(
            description="test types remain available for later sibling queries",
            file_name="_test_types.py",
            query_first=False,
            expected_parse_count=1,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_project_query_order_when_parsing_then_retains_only_required_modules(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ProjectRetentionTestCase,
) -> None:
    path: Path = tmp_path / "src/pkg/domain" / test_case.file_name
    path.parent.mkdir(parents=True)
    path.write_text("def phase() -> int:\n    return 1\n", encoding="utf-8")
    scoped_file: ScopedFile = ScopedFile(
        path=path,
        root=tmp_path / "src/pkg",
        scope=ScopeName.ROOT,
        relative_parts=("domain", test_case.file_name),
    )
    project: EvaluationProjectAnalysis = build_project_analysis(
        tree=DiscoveredTree(files=(scoped_file,), repo_root=RepoRoot(tmp_path))
    )
    parse_counts: list[int] = [0]

    def count_parse(candidate: ScopedFile) -> ParsedModule:
        parse_counts[0] += 1
        return parse_scoped_file(candidate)

    monkeypatch.setattr(
        "strata.evaluation.core.helpers.project_analysis.parse_scoped_file",
        count_parse,
    )

    analysis, parsed = exercise_project_parse_order(
        project=project,
        scoped_file=scoped_file,
        query_first=test_case.query_first,
    )

    assert analysis is not None
    assert parsed.scoped_file.path == path
    assert parse_counts[0] == test_case.expected_parse_count


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectParseContractTestCase(
            description="malformed discovered source is tolerant for queries and strict normally",
            source="def broken(:\n",
            expected_error_type=ParseError,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_malformed_discovered_file_when_querying_then_only_normal_parse_raises(
    tmp_path: Path,
    test_case: ProjectParseContractTestCase,
) -> None:
    path: Path = tmp_path / "src/pkg/domain/broken.py"
    path.parent.mkdir(parents=True)
    path.write_text(test_case.source, encoding="utf-8")
    scoped_file: ScopedFile = ScopedFile(
        path=path,
        root=tmp_path / "src/pkg",
        scope=ScopeName.ROOT,
        relative_parts=("domain", "broken.py"),
    )
    project: EvaluationProjectAnalysis = build_project_analysis(
        tree=DiscoveredTree(files=(scoped_file,), repo_root=RepoRoot(tmp_path))
    )

    analysis: Analysis | None = project.analysis(requester=path, path=path)

    assert analysis is None
    with pytest.raises(test_case.expected_error_type):
        project.parsed_module(scoped_file)
