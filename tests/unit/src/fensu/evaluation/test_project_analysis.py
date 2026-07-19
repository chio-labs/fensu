"""Tests for evaluation-scoped project analysis behavior."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from fensu.analysis.models import DataclassFact, ProjectDependency, ProjectFunctionFact
from fensu.analysis.types import Analysis
from fensu.discovery.models import DiscoveredTree, RepoRoot, ScopedFile
from fensu.discovery.types import ScopeName
from fensu.evaluation._helpers.parsing import parse_scoped_file
from fensu.evaluation._helpers.project_analysis import build_project_analysis
from fensu.evaluation.exceptions import ParseError
from fensu.evaluation.models import ParsedModule, SourceSnapshot
from fensu.evaluation.types import EvaluationProjectAnalysis
from tests.unit.src.fensu.evaluation._test_types import (
    ProjectDependencyTestCase,
    ProjectDirectoryQueryTestCase,
    ProjectParseContractTestCase,
    ProjectRetentionTestCase,
    ProjectScalarQueryTestCase,
    ProjectSourceQueryTestCase,
)
from tests.unit.src.fensu.evaluation.helpers import (
    exercise_project_parse_order,
    make_project_layout,
)


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectDependencyTestCase(
            description="missing module records every precedence candidate",
            module_name="pkg.phases",
            expected_dependency_paths=(
                "src/pkg/phases.py",
                "src/pkg/phases/__init__.py",
            ),
            expected_dependency_kinds=("is_file", "is_file"),
            expected_dependency_answers=(False, False),
        ),
        ProjectDependencyTestCase(
            description="module probes only its matching configured package root",
            module_name="shared.phases",
            expected_dependency_paths=(
                "lib/shared/phases.py",
                "lib/shared/phases/__init__.py",
            ),
            expected_dependency_kinds=("is_file", "is_file"),
            expected_dependency_answers=(False, False),
            runtime_roots=("services/acme", "lib/shared"),
        ),
        ProjectDependencyTestCase(
            description="module probes a configured test package root",
            module_name="qa.unit.helpers",
            expected_dependency_paths=(
                "qa/unit/helpers.py",
                "qa/unit/helpers/__init__.py",
            ),
            expected_dependency_kinds=("is_file", "is_file"),
            expected_dependency_answers=(False, False),
            test_roots=("qa",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_missing_module_when_querying_then_records_all_candidate_dependencies(
    tmp_path: Path,
    test_case: ProjectDependencyTestCase,
) -> None:
    requester: Path = tmp_path / "src/pkg/main/run.py"
    project: EvaluationProjectAnalysis = build_project_analysis(
        tree=DiscoveredTree(
            files=(),
            repo_root=RepoRoot(tmp_path),
            layout=make_project_layout(
                repo_root=tmp_path,
                runtime_roots=test_case.runtime_roots,
                test_roots=test_case.test_roots,
            ),
        )
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
    assert (
        tuple(item.dependency.relative_to(tmp_path).as_posix() for item in dependencies)
        == test_case.expected_dependency_paths
    )
    assert tuple(item.kind for item in dependencies) == test_case.expected_dependency_kinds
    assert tuple(item.answer for item in dependencies) == test_case.expected_dependency_answers


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
        tree=DiscoveredTree(
            files=(),
            repo_root=RepoRoot(tmp_path),
            layout=make_project_layout(repo_root=tmp_path),
        )
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
    (package / "later.py").write_text("", encoding="utf-8")
    repeated_direct: tuple[Path, ...] = project.glob(
        requester=requester,
        path=package,
        pattern="*.py",
    )
    repeated_recursive: tuple[Path, ...] = project.glob(
        requester=requester,
        path=package,
        pattern="*.py",
        recursive=True,
    )
    dependencies: tuple[ProjectDependency, ...] = project.dependencies()

    assert tuple(sorted(path.name for path in entries)) == test_case.expected_entry_names
    assert repeated_entries == entries
    assert tuple(path.name for path in direct_matches) == test_case.expected_direct_matches
    assert (
        tuple(path.relative_to(package).as_posix() for path in recursive_matches)
        == test_case.expected_recursive_matches
    )
    assert no_matches == ()
    assert repeated_direct == direct_matches
    assert repeated_recursive == recursive_matches
    assert tuple(item.kind for item in dependencies) == test_case.expected_dependency_kinds
    assert tuple(item.pattern for item in dependencies) == test_case.expected_patterns
    assert tuple(item.recursive for item in dependencies) == test_case.expected_recursive
    assert all(item.query_path == package for item in dependencies)
    assert all(item.dependency == package.resolve() for item in dependencies)
    assert tuple(item.answer for item in dependencies) == (
        entries,
        direct_matches,
        recursive_matches,
        no_matches,
    )


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectScalarQueryTestCase(
            description="scalar queries record the exact returned booleans",
            expected_dependency_kinds=("exists", "is_file", "is_dir"),
            expected_dependency_answers=(True, False, True),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_scalar_queries_when_observing_then_records_returned_answers(
    tmp_path: Path,
    test_case: ProjectScalarQueryTestCase,
) -> None:
    package: Path = tmp_path / "src/pkg/domain"
    package.mkdir(parents=True)
    requester: Path = tmp_path / "src/pkg/main/run.py"
    project: EvaluationProjectAnalysis = build_project_analysis(
        tree=DiscoveredTree(
            files=(),
            repo_root=RepoRoot(tmp_path),
            layout=make_project_layout(repo_root=tmp_path),
        )
    )

    exists: bool = project.exists(requester=requester, path=package)
    is_file: bool = project.is_file(requester=requester, path=package)
    is_dir: bool = project.is_dir(requester=requester, path=package)
    package.rmdir()
    frozen_answers: tuple[bool, ...] = (
        project.exists(requester=requester, path=package),
        project.is_file(requester=requester, path=package),
        project.is_dir(requester=requester, path=package),
    )
    dependencies: tuple[ProjectDependency, ...] = project.dependencies()

    assert (exists, is_file, is_dir) == test_case.expected_dependency_answers
    assert frozen_answers == test_case.expected_dependency_answers
    assert tuple(item.kind for item in dependencies) == test_case.expected_dependency_kinds
    assert tuple(item.answer for item in dependencies) == test_case.expected_dependency_answers


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSourceQueryTestCase(
            description="source answer is frozen and retained for each requester",
            source="value: int = 1\n",
            mutated_source="value: int = 2\n",
            expected_dependency_count=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_repeated_source_query_when_source_mutates_then_reuses_first_answer(
    tmp_path: Path,
    test_case: ProjectSourceQueryTestCase,
) -> None:
    path: Path = tmp_path / "src/pkg/domain/models.py"
    path.parent.mkdir(parents=True)
    path.write_bytes(test_case.source.encode("utf-8"))
    project: EvaluationProjectAnalysis = build_project_analysis(
        tree=DiscoveredTree(
            files=(),
            repo_root=RepoRoot(tmp_path),
            layout=make_project_layout(repo_root=tmp_path),
        )
    )

    first: Analysis | None = project.analysis(requester=path.parent / "first.py", path=path)
    path.write_bytes(test_case.mutated_source.encode("utf-8"))
    second: Analysis | None = project.analysis(requester=path.parent / "second.py", path=path)
    dependencies: tuple[ProjectDependency, ...] = project.dependencies()
    expected_answer: str = hashlib.sha256(test_case.source.encode("utf-8")).hexdigest()

    assert first is second
    assert len(dependencies) == test_case.expected_dependency_count
    assert tuple(item.answer for item in dependencies) == (expected_answer, expected_answer)


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
        tree=DiscoveredTree(
            files=(scoped_file,),
            repo_root=RepoRoot(tmp_path),
            layout=make_project_layout(repo_root=tmp_path),
        )
    )
    parse_counts: list[int] = [0]

    def count_parse(
        *,
        scoped_file: ScopedFile,
        source_snapshot: SourceSnapshot | None = None,
    ) -> ParsedModule:
        parse_counts[0] += 1
        return parse_scoped_file(scoped_file=scoped_file, source_snapshot=source_snapshot)

    monkeypatch.setattr(
        "fensu.evaluation._helpers.project_analysis.parse_scoped_file",
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
        ProjectRetentionTestCase(
            description="test types retain dataclass facts without retaining their parsed module",
            file_name="_test_types.py",
            query_first=False,
            expected_parse_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_parsed_test_types_when_querying_dataclasses_then_reuses_fact_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ProjectRetentionTestCase,
) -> None:
    path: Path = tmp_path / "tests/unit/src/pkg/domain" / test_case.file_name
    path.parent.mkdir(parents=True)
    path.write_text(
        "@dataclass(frozen=True)\nclass ExampleTestCase:\n    description: str\n",
        encoding="utf-8",
    )
    scoped_file: ScopedFile = ScopedFile(
        path=path,
        root=tmp_path / "tests/unit/src/pkg",
        scope=ScopeName.TEST,
        relative_parts=("domain", test_case.file_name),
    )
    project: EvaluationProjectAnalysis = build_project_analysis(
        tree=DiscoveredTree(
            files=(scoped_file,),
            repo_root=RepoRoot(tmp_path),
            layout=make_project_layout(repo_root=tmp_path, test_roots=("tests",)),
        )
    )
    parse_counts: list[int] = [0]

    def count_parse(*, scoped_file: ScopedFile) -> ParsedModule:
        parse_counts[0] += 1
        return parse_scoped_file(scoped_file=scoped_file)

    monkeypatch.setattr(
        "fensu.evaluation._helpers.project_analysis.parse_scoped_file",
        count_parse,
    )

    parsed: ParsedModule = project.parsed_module(scoped_file)
    dataclasses: tuple[DataclassFact, ...] = project.dataclasses(
        requester=path.parent / "test_example.py",
        path=path,
    )

    assert parsed.scoped_file.path == path
    assert tuple(fact.name for fact in dataclasses) == ("ExampleTestCase",)
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
    path.write_bytes(test_case.source.encode("utf-8"))
    scoped_file: ScopedFile = ScopedFile(
        path=path,
        root=tmp_path / "src/pkg",
        scope=ScopeName.ROOT,
        relative_parts=("domain", "broken.py"),
    )
    project: EvaluationProjectAnalysis = build_project_analysis(
        tree=DiscoveredTree(
            files=(scoped_file,),
            repo_root=RepoRoot(tmp_path),
            layout=make_project_layout(repo_root=tmp_path),
        )
    )

    analysis: Analysis | None = project.analysis(requester=path, path=path)

    assert analysis is None
    dependencies: tuple[ProjectDependency, ...] = project.dependencies()
    assert dependencies[0].answer == hashlib.sha256(test_case.source.encode("utf-8")).hexdigest()
    with pytest.raises(test_case.expected_error_type):
        project.parsed_module(scoped_file)
