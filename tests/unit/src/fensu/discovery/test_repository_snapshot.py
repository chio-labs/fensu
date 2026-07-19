"""Behavior tests for the discovery-owned repository snapshot table."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.discovery.classes.repository_snapshot import RepositorySnapshot
from fensu.discovery.main.discover_files import _snapshot_relative_paths
from fensu.discovery.models import RepoRoot, ScopedFile
from fensu.discovery.types import ScopeName
from fensu.instrumentation.constants import SNAPSHOT_ROOT_RELATIVIZE_OPERATION
from fensu.instrumentation.main.measure_operations import measure_operations
from tests.unit.src.fensu.discovery._test_types import (
    SnapshotHashTestCase,
    SnapshotInstallScaleTestCase,
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
        relative_by_path={
            str(tmp_path / relative): relative for relative in test_case.installed_relative_paths
        },
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
    snapshot.install(repo_root=tmp_path, relative_by_path={str(target): "src/pkg/a.py"})
    seed_actions: dict[bool, tuple[dict[str, str], ...]] = {
        False: (),
        True: ({str(target): "abc123"},),
    }
    for seed in seed_actions[test_case.seeded]:
        snapshot.seed_hashes(hash_by_path=seed)
    reinstall_actions: dict[bool, tuple[Path, ...]] = {False: (), True: (target,)}
    for _ in reinstall_actions[test_case.reinstalled]:
        snapshot.install(repo_root=tmp_path, relative_by_path={str(target): "src/pkg/a.py"})

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
        relative_by_path={
            str(tmp_path / relative): relative for relative in test_case.installed_relative_paths
        },
    )
    snapshot.clear()

    relative: str | None = snapshot.relative_path(
        path=tmp_path / test_case.query_relative_path,
        repo_root=tmp_path,
    )

    assert relative == test_case.expected_relative


@pytest.mark.parametrize(
    "test_case",
    [
        SnapshotInstallScaleTestCase(
            description="snapshot relativization scales with roots rather than files",
            files_per_root=4,
            expected_root_relativizations=2,
            expected_installed_paths=8,
            expected_relative_path="src/pkg/domain_3/models.py",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_scoped_files_when_building_snapshot_paths_then_relativizes_each_root_once(
    test_case: SnapshotInstallScaleTestCase,
    tmp_path: Path,
) -> None:
    runtime_root: Path = tmp_path / "src/pkg"
    test_root: Path = tmp_path / "tests"
    scoped_file_list: list[ScopedFile] = []
    for root, scope in ((runtime_root, ScopeName.ROOT), (test_root, ScopeName.TEST)):
        for index in range(test_case.files_per_root):
            scoped_file_list.append(
                ScopedFile(
                    path=root / f"domain_{index}/models.py",
                    root=root,
                    scope=scope,
                    relative_parts=(f"domain_{index}", "models.py"),
                )
            )
    scoped_files: tuple[ScopedFile, ...] = tuple(scoped_file_list)
    external_path: Path = tmp_path.parent / "external.py"
    scoped_files = (
        *scoped_files,
        ScopedFile(
            path=external_path,
            root=runtime_root,
            scope=ScopeName.ROOT,
            relative_parts=("linked.py",),
        ),
    )
    relative_by_path: dict[str, str] = {}
    counts: dict[str, int] = measure_operations(
        operation=lambda: relative_by_path.update(
            _snapshot_relative_paths(repo_root=RepoRoot(path=tmp_path), files=scoped_files)
        )
    )

    assert counts[SNAPSHOT_ROOT_RELATIVIZE_OPERATION] == (test_case.expected_root_relativizations)
    assert len(relative_by_path) == test_case.expected_installed_paths
    assert str(external_path) not in relative_by_path
    assert relative_by_path[str(runtime_root / "domain_3/models.py")] == (
        test_case.expected_relative_path
    )
