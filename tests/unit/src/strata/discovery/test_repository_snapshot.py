"""Behavior tests for the discovery-owned repository snapshot table."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.discovery.classes.repository_snapshot import RepositorySnapshot
from tests.unit.src.strata.discovery._test_types import (
    SnapshotHashTestCase,
    SnapshotRelativePathTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        SnapshotRelativePathTestCase(
            description="installed file resolves to its posix relative spelling",
            installed_relative_paths=("src/pkg/a.py", "src/pkg/deep/b.py"),
            query_relative_path="src/pkg/deep/b.py",
            query_foreign_root=False,
            expected_relative="src/pkg/deep/b.py",
        ),
        SnapshotRelativePathTestCase(
            description="uninstalled file misses the table",
            installed_relative_paths=("src/pkg/a.py",),
            query_relative_path="src/pkg/other.py",
            query_foreign_root=False,
            expected_relative=None,
        ),
        SnapshotRelativePathTestCase(
            description="foreign repository root misses the table",
            installed_relative_paths=("src/pkg/a.py",),
            query_relative_path="src/pkg/a.py",
            query_foreign_root=True,
            expected_relative=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_installed_snapshot_when_looking_up_relative_path_then_returns_expected(
    test_case: SnapshotRelativePathTestCase,
    tmp_path: Path,
) -> None:
    snapshot: RepositorySnapshot = RepositorySnapshot()
    snapshot.install(
        repo_root=tmp_path,
        canonical_paths=tuple(
            tmp_path / relative for relative in test_case.installed_relative_paths
        ),
    )
    query_root: Path = {False: tmp_path, True: tmp_path / "elsewhere"}[test_case.query_foreign_root]

    relative: str | None = snapshot.relative_path(
        path=tmp_path / test_case.query_relative_path,
        repo_root=query_root,
    )

    assert relative == test_case.expected_relative


@pytest.mark.parametrize(
    "test_case",
    [
        SnapshotHashTestCase(
            description="seeded hash is returned for the canonical spelling",
            seeded=True,
            reinstalled=False,
            expected_hash="abc123",
        ),
        SnapshotHashTestCase(
            description="unseeded hash lookup misses",
            seeded=False,
            reinstalled=False,
            expected_hash=None,
        ),
        SnapshotHashTestCase(
            description="reinstalling the snapshot clears seeded hashes",
            seeded=True,
            reinstalled=True,
            expected_hash=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_seeded_hashes_when_looking_up_then_returns_expected(
    test_case: SnapshotHashTestCase,
    tmp_path: Path,
) -> None:
    snapshot: RepositorySnapshot = RepositorySnapshot()
    target: Path = tmp_path / "src/pkg/a.py"
    snapshot.install(repo_root=tmp_path, canonical_paths=(target,))
    seed_actions: dict[bool, tuple[dict[str, str], ...]] = {
        False: (),
        True: ({str(target): "abc123"},),
    }
    for seed in seed_actions[test_case.seeded]:
        snapshot.seed_hashes(hash_by_path=seed)
    reinstall_actions: dict[bool, tuple[Path, ...]] = {False: (), True: (target,)}
    for _ in reinstall_actions[test_case.reinstalled]:
        snapshot.install(repo_root=tmp_path, canonical_paths=(target,))

    assert snapshot.source_hash(path=target) == test_case.expected_hash


@pytest.mark.parametrize(
    "test_case",
    [
        SnapshotRelativePathTestCase(
            description="clearing the table forgets installed paths",
            installed_relative_paths=("src/pkg/a.py",),
            query_relative_path="src/pkg/a.py",
            query_foreign_root=False,
            expected_relative=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cleared_snapshot_when_looking_up_then_misses(
    test_case: SnapshotRelativePathTestCase,
    tmp_path: Path,
) -> None:
    snapshot: RepositorySnapshot = RepositorySnapshot()
    snapshot.install(
        repo_root=tmp_path,
        canonical_paths=tuple(
            tmp_path / relative for relative in test_case.installed_relative_paths
        ),
    )
    snapshot.clear()

    relative: str | None = snapshot.relative_path(
        path=tmp_path / test_case.query_relative_path,
        repo_root=tmp_path,
    )

    assert relative == test_case.expected_relative
