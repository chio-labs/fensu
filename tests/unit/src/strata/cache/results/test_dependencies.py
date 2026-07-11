"""Tests for persisted project-query dependency re-observation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

import strata.cache.results.helpers.dependencies as dependency_module
from strata.analysis.core.types import ProjectDependencyKind
from strata.cache.fingerprints.main.source import fingerprint_source
from strata.cache.results.helpers.dependencies import dependencies_are_current
from strata.cache.results.models import DependencyObservation
from strata.cache.results.types import DependencyStateCache
from tests.unit.src.strata.cache.results._test_types import (
    DependencyInvalidationTestCase,
    DependencyReuseTestCase,
    GlobDependencyInvalidationTestCase,
    ScalarDependencyInvalidationTestCase,
)
from tests.unit.src.strata.cache.results.helpers import (
    add_glob_match,
    glob_answer,
    mutate_scalar_target,
    scalar_observation,
)


@pytest.mark.parametrize(
    "test_case",
    [
        DependencyInvalidationTestCase(
            description="same-length source edit invalidates complete content answer",
            expected_before=True,
            expected_after=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_source_observation_when_content_changes_then_invalidates(
    tmp_path: Path,
    test_case: DependencyInvalidationTestCase,
) -> None:
    path: Path = tmp_path / "dependency.py"
    path.write_bytes(b"value = 1\n")
    observation: DependencyObservation = DependencyObservation(
        requester_path="src/pkg/models.py",
        query_path="dependency.py",
        dependency_path="dependency.py",
        kind=ProjectDependencyKind.SOURCE,
        answer=fingerprint_source(path.read_bytes()).value,
    )

    before: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)
    path.write_bytes(b"value = 2\n")
    after: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)

    assert before is test_case.expected_before
    assert after is test_case.expected_after


@pytest.mark.parametrize(
    "test_case",
    [
        DependencyInvalidationTestCase(
            description="previously missing source creation invalidates negative answer",
            expected_before=True,
            expected_after=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_missing_source_observation_when_file_appears_then_invalidates(
    tmp_path: Path,
    test_case: DependencyInvalidationTestCase,
) -> None:
    observation: DependencyObservation = DependencyObservation(
        requester_path="src/pkg/models.py",
        query_path="missing.py",
        dependency_path="missing.py",
        kind=ProjectDependencyKind.SOURCE,
        answer=None,
    )

    before: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)
    (tmp_path / "missing.py").write_text("value = 1\n", encoding="utf-8")
    after: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)

    assert before is test_case.expected_before
    assert after is test_case.expected_after


@pytest.mark.parametrize(
    "test_case",
    [
        DependencyInvalidationTestCase(
            description="previously missing module candidate creation invalidates file probe",
            expected_before=True,
            expected_after=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_missing_file_probe_when_candidate_appears_then_invalidates(
    tmp_path: Path,
    test_case: DependencyInvalidationTestCase,
) -> None:
    observation: DependencyObservation = DependencyObservation(
        requester_path="src/pkg/models.py",
        query_path="module.py",
        dependency_path="module.py",
        kind=ProjectDependencyKind.IS_FILE,
        answer=False,
    )

    before: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)
    (tmp_path / "module.py").write_text("value = 1\n", encoding="utf-8")
    after: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)

    assert before is test_case.expected_before
    assert after is test_case.expected_after


@pytest.mark.parametrize(
    "test_case",
    [
        ScalarDependencyInvalidationTestCase(
            description="existing path deletion invalidates exists answer",
            kind=ProjectDependencyKind.EXISTS,
            expected_before=True,
            expected_after=False,
        ),
        ScalarDependencyInvalidationTestCase(
            description="file replacement by directory invalidates file answer",
            kind=ProjectDependencyKind.IS_FILE,
            expected_before=True,
            expected_after=False,
        ),
        ScalarDependencyInvalidationTestCase(
            description="directory replacement by file invalidates directory answer",
            kind=ProjectDependencyKind.IS_DIR,
            expected_before=True,
            expected_after=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_scalar_observation_when_path_type_changes_then_invalidates(
    tmp_path: Path,
    test_case: ScalarDependencyInvalidationTestCase,
) -> None:
    observation: DependencyObservation = scalar_observation(
        repo_root=tmp_path,
        kind=test_case.kind,
    )

    before: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)
    mutate_scalar_target(repo_root=tmp_path, kind=test_case.kind)
    after: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)

    assert before is test_case.expected_before
    assert after is test_case.expected_after


@pytest.mark.parametrize(
    "test_case",
    [
        DependencyInvalidationTestCase(
            description="direct child creation invalidates directory namespace",
            expected_before=True,
            expected_after=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_directory_observation_when_child_appears_then_invalidates(
    tmp_path: Path,
    test_case: DependencyInvalidationTestCase,
) -> None:
    package: Path = tmp_path / "pkg"
    package.mkdir()
    first: Path = package / "first.py"
    first.write_text("", encoding="utf-8")
    observation: DependencyObservation = DependencyObservation(
        requester_path="src/pkg/models.py",
        query_path="pkg",
        dependency_path="pkg",
        kind=ProjectDependencyKind.DIRECTORY_ENTRIES,
        answer=("pkg/first.py",),
    )

    before: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)
    (package / "later.py").write_text("", encoding="utf-8")
    after: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)

    assert before is test_case.expected_before
    assert after is test_case.expected_after


@pytest.mark.parametrize(
    "test_case",
    [
        GlobDependencyInvalidationTestCase(
            description="direct match creation invalidates direct glob",
            recursive=False,
            expected_before=True,
            expected_after=False,
        ),
        GlobDependencyInvalidationTestCase(
            description="nested match creation invalidates recursive glob",
            recursive=True,
            expected_before=True,
            expected_after=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_glob_observation_when_match_appears_then_invalidates(
    tmp_path: Path,
    test_case: GlobDependencyInvalidationTestCase,
) -> None:
    package: Path = tmp_path / "pkg"
    package.mkdir()
    (package / "first.py").write_text("", encoding="utf-8")
    observation: DependencyObservation = DependencyObservation(
        requester_path="src/pkg/models.py",
        query_path="pkg",
        dependency_path="pkg",
        kind=ProjectDependencyKind.GLOB,
        answer=glob_answer(repo_root=tmp_path, recursive=test_case.recursive),
        pattern="*.py",
        recursive=test_case.recursive,
    )

    before: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)
    add_glob_match(repo_root=tmp_path, recursive=test_case.recursive)
    after: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)

    assert before is test_case.expected_before
    assert after is test_case.expected_after


@pytest.mark.parametrize(
    "test_case",
    [
        DependencyInvalidationTestCase(
            description="symlink retarget invalidates unchanged file-type answer",
            expected_before=True,
            expected_after=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_symlink_observation_when_target_changes_then_invalidates(
    tmp_path: Path,
    test_case: DependencyInvalidationTestCase,
) -> None:
    first: Path = tmp_path / "first.py"
    second: Path = tmp_path / "second.py"
    first.write_text("", encoding="utf-8")
    second.write_text("", encoding="utf-8")
    link: Path = tmp_path / "link.py"
    link.symlink_to(first)
    observation: DependencyObservation = DependencyObservation(
        requester_path="src/pkg/models.py",
        query_path="link.py",
        dependency_path="first.py",
        kind=ProjectDependencyKind.IS_FILE,
        answer=True,
    )

    before: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)
    link.unlink()
    link.symlink_to(second)
    after: bool = dependencies_are_current(observations=(observation,), repo_root=tmp_path)

    assert before is test_case.expected_before
    assert after is test_case.expected_after


@pytest.mark.parametrize(
    "test_case",
    [
        DependencyReuseTestCase(
            description="equivalent requester queries share one filesystem observation",
            requester_paths=("src/pkg/first.py", "src/pkg/second.py"),
            expected_current=True,
            expected_observation_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_equivalent_dependency_queries_when_validating_batch_then_reuses_observation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: DependencyReuseTestCase,
) -> None:
    observations: tuple[DependencyObservation, ...] = tuple(
        DependencyObservation(
            requester_path=requester_path,
            query_path="missing.py",
            dependency_path="missing.py",
            kind=ProjectDependencyKind.EXISTS,
            answer=False,
        )
        for requester_path in test_case.requester_paths
    )
    observer: Mock = Mock(wraps=dependency_module._reobserve)
    monkeypatch.setattr(dependency_module, "_reobserve", observer)
    states: DependencyStateCache = {}

    current: bool = dependencies_are_current(
        observations=observations,
        repo_root=tmp_path,
        states=states,
    )

    assert current is test_case.expected_current
    assert observer.call_count == test_case.expected_observation_count
