"""Separate-process end-to-end tests for persistent check caching."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from fensu.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH
from tests.e2e.src.fensu.cli.main._test_types import (
    CacheCliTestCase,
    CacheColorCliTestCase,
    CacheDependencyCliTestCase,
    CacheManifestCliTestCase,
    CacheMutationCliTestCase,
    CliProjectFile,
)
from tests.e2e.src.fensu.cli.main.helpers import (
    cache_snapshot,
    corrupt_result_cache_record,
    remove_check_output_record,
    run_cli_check,
    run_cli_terminal_check,
    write_cli_project,
)


@pytest.mark.skipif(not hasattr(os, "openpty"), reason="pseudo-terminal is required")
@pytest.mark.parametrize(
    "test_case",
    [
        CacheColorCliTestCase(
            description="plain cached report does not suppress terminal color",
            config='roots = ["src/pkg"]\ntests = []\nselect = ["FFA101"]\n',
            files=(CliProjectFile(relative_path="src/pkg/models.py", source="VALUE: int = 1\n"),),
            expected_exit_code=0,
            expected_plain_stdout="Found 0 faults\n",
            expected_color_fragment="\033[1;32mFound 0 faults\033[0m",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_plain_cached_report_when_checking_on_terminal_then_output_is_colored(
    tmp_path: Path,
    test_case: CacheColorCliTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=tuple((file.relative_path, file.source) for file in test_case.files),
    )
    plain: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))

    exit_code, terminal_output = run_cli_terminal_check(root=tmp_path, argv=("--cache",))

    assert plain.returncode == test_case.expected_exit_code
    assert plain.stdout == test_case.expected_plain_stdout
    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_color_fragment in terminal_output


@pytest.mark.parametrize(
    "test_case",
    [
        CacheCliTestCase(
            description="cold warm and no-cache installed processes remain byte-identical",
            config='roots = ["src/pkg"]\ntests = []\nselect = ["FFA101"]\n',
            files=(CliProjectFile(relative_path="src/pkg/models.py", source="VALUE = 1\n"),),
            expected_exit_code=1,
            expected_stdout_fragment="FFA101",
            expected_cache_exists=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cacheable_project_when_running_separate_modes_then_preserves_output_and_cache(
    tmp_path: Path,
    test_case: CacheCliTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=tuple((file.relative_path, file.source) for file in test_case.files),
    )

    cold: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))
    cold_snapshot: tuple[tuple[str, bytes], ...] = cache_snapshot(tmp_path)
    warm_stats: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=("--cache", "--cache-stats"),
    )
    warm: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))
    warm_snapshot: tuple[tuple[str, bytes], ...] = cache_snapshot(tmp_path)
    uncached: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=("--no-cache",),
    )
    uncached_snapshot: tuple[tuple[str, bytes], ...] = cache_snapshot(tmp_path)

    assert cold.returncode == test_case.expected_exit_code
    assert warm.returncode == test_case.expected_exit_code
    assert warm_stats.returncode == test_case.expected_exit_code
    assert uncached.returncode == test_case.expected_exit_code
    assert test_case.expected_stdout_fragment in cold.stdout
    assert warm.stdout == cold.stdout
    assert warm.stderr == cold.stderr
    assert warm_stats.stdout == cold.stdout
    assert "hits=1 misses=0" in warm_stats.stderr
    assert uncached.stdout == cold.stdout
    assert uncached.stderr == cold.stderr
    assert bool(cold_snapshot) is test_case.expected_cache_exists
    assert warm_snapshot == cold_snapshot
    assert uncached_snapshot == cold_snapshot


@pytest.mark.parametrize(
    "test_case",
    [
        CacheCliTestCase(
            description="warning mode is byte-identical across cold warm and uncached processes",
            config=('roots = ["src/pkg"]\ntests = []\nselect = ["FFA101"]\nwarn = ["FFA002"]\n'),
            files=(
                CliProjectFile(
                    relative_path="src/pkg/module.py",
                    source="def build():\n    return 1\n",
                ),
            ),
            expected_exit_code=0,
            expected_stdout_fragment="Found 0 faults and 1 warning",
            expected_cache_exists=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_warning_project_when_running_installed_modes_then_preserves_advisory_output(
    tmp_path: Path,
    test_case: CacheCliTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=tuple((file.relative_path, file.source) for file in test_case.files),
    )

    plain: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=("--no-cache",),
    )
    cold: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=("--cache", "--warn"),
    )
    warm_stats: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=("--cache", "--cache-stats", "--warn"),
    )
    uncached: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=("--no-cache", "--warn"),
    )

    assert plain.returncode == test_case.expected_exit_code
    assert plain.stdout == "Found 0 faults\n"
    assert cold.returncode == test_case.expected_exit_code
    assert warm_stats.returncode == test_case.expected_exit_code
    assert uncached.returncode == test_case.expected_exit_code
    assert test_case.expected_stdout_fragment in cold.stdout
    assert warm_stats.stdout == cold.stdout
    assert uncached.stdout == cold.stdout
    assert "hits=1 misses=0" in warm_stats.stderr
    assert bool(cache_snapshot(tmp_path)) is test_case.expected_cache_exists


@pytest.mark.parametrize(
    "test_case",
    [
        CacheCliTestCase(
            description="fresh no-cache installed process creates no cache namespace",
            config='roots = ["src/pkg"]\ntests = []\nselect = ["FFA101"]\n',
            files=(CliProjectFile(relative_path="src/pkg/models.py", source="VALUE = 1\n"),),
            expected_exit_code=1,
            expected_stdout_fragment="FFA101",
            expected_cache_exists=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_fresh_project_when_running_installed_no_cache_then_creates_no_storage(
    tmp_path: Path,
    test_case: CacheCliTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=tuple((file.relative_path, file.source) for file in test_case.files),
    )

    completed: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=("--no-cache",),
    )

    assert completed.returncode == test_case.expected_exit_code
    assert test_case.expected_stdout_fragment in completed.stdout
    assert (tmp_path / ".fensu").exists() is test_case.expected_cache_exists


@pytest.mark.parametrize(
    "test_case",
    [
        CacheMutationCliTestCase(
            description="same-length source mutation with restored timestamp invalidates",
            config='roots = ["src/pkg"]\ntests = []\nselect = ["FFA101"]\n',
            relative_path="src/pkg/models.py",
            first_source="VALUE = 1\n",
            second_source="OTHER = 1\n",
            expected_exit_code=1,
            expected_first_fragment="VALUE = 1",
            expected_second_fragment="OTHER = 1",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_published_source_when_content_changes_then_installed_process_invalidates(
    tmp_path: Path,
    test_case: CacheMutationCliTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=((test_case.relative_path, test_case.first_source),),
    )
    path: Path = tmp_path / test_case.relative_path
    original_stat: os.stat_result = path.stat()

    first: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))
    path.write_text(test_case.second_source, encoding="utf-8")
    os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    second: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))

    assert first.returncode == test_case.expected_exit_code
    assert second.returncode == test_case.expected_exit_code
    assert test_case.expected_first_fragment in first.stdout
    assert test_case.expected_second_fragment in second.stdout
    assert test_case.expected_first_fragment not in second.stdout


@pytest.mark.parametrize(
    "test_case",
    [
        CacheCliTestCase(
            description="malformed result record becomes miss with identical diagnostics",
            config='roots = ["src/pkg"]\ntests = []\nselect = ["FFA101"]\n',
            files=(CliProjectFile(relative_path="src/pkg/models.py", source="VALUE = 1\n"),),
            expected_exit_code=1,
            expected_stdout_fragment="FFA101",
            expected_cache_exists=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_malformed_result_when_running_installed_check_then_recomputes_identically(
    tmp_path: Path,
    test_case: CacheCliTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=tuple((file.relative_path, file.source) for file in test_case.files),
    )
    first: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))
    corrupted_key: str = corrupt_result_cache_record(tmp_path)
    _ = remove_check_output_record(tmp_path)

    second: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))

    assert first.returncode == test_case.expected_exit_code
    assert second.returncode == test_case.expected_exit_code
    assert test_case.expected_stdout_fragment in second.stdout
    assert second.stdout == first.stdout
    assert second.stderr == first.stderr
    assert dict(cache_snapshot(tmp_path))[corrupted_key] != b"{"
    assert bool(cache_snapshot(tmp_path)) is test_case.expected_cache_exists


@pytest.mark.parametrize(
    "test_case",
    [
        CacheCliTestCase(
            description="corrupt SQLite database degrades and rebuilds without changing diagnostics",
            config='roots = ["src/pkg"]\ntests = []\nselect = ["FFA101"]\n',
            files=(CliProjectFile(relative_path="src/pkg/models.py", source="VALUE = 1\n"),),
            expected_exit_code=1,
            expected_stdout_fragment="FFA101",
            expected_cache_exists=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_corrupt_database_when_running_installed_check_then_degrades_and_rebuilds(
    tmp_path: Path,
    test_case: CacheCliTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=tuple((file.relative_path, file.source) for file in test_case.files),
    )
    first: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))
    database: Path = tmp_path / CACHE_DATABASE_RELATIVE_PATH
    database.write_bytes(b"not a sqlite database")

    degraded: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))
    database.unlink()
    rebuilt: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))

    assert first.returncode == test_case.expected_exit_code
    assert degraded.returncode == test_case.expected_exit_code
    assert rebuilt.returncode == test_case.expected_exit_code
    assert degraded.stdout == first.stdout
    assert rebuilt.stdout == first.stdout
    assert "cache publication failed" in degraded.stderr
    assert rebuilt.stderr == first.stderr
    assert test_case.expected_stdout_fragment in rebuilt.stdout
    assert bool(cache_snapshot(tmp_path)) is test_case.expected_cache_exists


@pytest.mark.parametrize(
    "test_case",
    [
        CacheManifestCliTestCase(
            description="new and deleted files update installed complete diagnostics",
            config='roots = ["src/pkg"]\ntests = []\nselect = ["FFA101"]\n',
            initial_paths=("src/pkg/a.py", "src/pkg/b.py"),
            final_paths=("src/pkg/a.py", "src/pkg/c.py"),
            expected_exit_code=1,
            expected_present_paths=("src/pkg/a.py", "src/pkg/c.py"),
            expected_absent_paths=("src/pkg/b.py",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_changed_manifest_when_running_installed_check_then_updates_complete_result(
    tmp_path: Path,
    test_case: CacheManifestCliTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=tuple((path, "VALUE = 1\n") for path in test_case.initial_paths),
    )
    _ = run_cli_check(root=tmp_path, argv=("--cache",))
    (tmp_path / "src/pkg/b.py").unlink()
    (tmp_path / "src/pkg/c.py").write_text("VALUE = 1\n", encoding="utf-8")

    completed: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=("--cache",),
    )

    assert completed.returncode == test_case.expected_exit_code
    assert all(path in completed.stdout for path in test_case.expected_present_paths)
    assert all(path not in completed.stdout for path in test_case.expected_absent_paths)


@pytest.mark.parametrize(
    "test_case",
    [
        CacheDependencyCliTestCase(
            description="previously missing test-types dependency creation invalidates requester",
            config=('roots = ["src/pkg"]\ntests = ["tests"]\ntooling = []\nselect = ["FFT204"]\n'),
            requester_path="tests/unit/src/pkg/test_example.py",
            requester_source="def test_example() -> None:\n    pass\n",
            dependency_path="tests/unit/src/pkg/_test_types.py",
            dependency_source="from dataclasses import dataclass\n",
            expected_first_exit_code=1,
            expected_second_exit_code=0,
            expected_first_fragment="FFT204",
            expected_second_fragment="Found 0 faults",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_negative_dependency_when_file_appears_then_installed_process_invalidates(
    tmp_path: Path,
    test_case: CacheDependencyCliTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=(
            ("src/pkg/__init__.py", ""),
            (test_case.requester_path, test_case.requester_source),
        ),
    )

    first: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))
    dependency: Path = tmp_path / test_case.dependency_path
    dependency.write_text(test_case.dependency_source, encoding="utf-8")
    second: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))

    assert first.returncode == test_case.expected_first_exit_code
    assert second.returncode == test_case.expected_second_exit_code
    assert test_case.expected_first_fragment in first.stdout
    assert test_case.expected_second_fragment in second.stdout


@pytest.mark.parametrize(
    "test_case",
    [
        CacheDependencyCliTestCase(
            description="entrypoint metadata change invalidates project-rule output",
            config=('roots = ["src/pkg"]\ntests = []\ntooling = []\nselect = ["FFL105"]\n'),
            requester_path="src/pkg/orders/billing/main/calculate.py",
            requester_source="def calculate() -> None:\n    pass\n",
            dependency_path="pyproject.toml",
            dependency_source=(
                '[project]\nname = "fixture"\n[project.scripts]\ncalculate = '
                '"pkg.orders.billing.main.calculate:calculate"\n'
            ),
            expected_first_exit_code=1,
            expected_second_exit_code=0,
            expected_first_fragment="FFL105",
            expected_second_fragment="Found 0 faults",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_entrypoint_metadata_when_changed_then_installed_cache_invalidates(
    tmp_path: Path,
    test_case: CacheDependencyCliTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=(
            ("src/pkg/__init__.py", ""),
            (test_case.requester_path, test_case.requester_source),
        ),
    )
    first: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))
    (tmp_path / test_case.dependency_path).write_text(
        test_case.dependency_source,
        encoding="utf-8",
    )

    second: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))

    assert first.returncode == test_case.expected_first_exit_code
    assert second.returncode == test_case.expected_second_exit_code
    assert test_case.expected_first_fragment in first.stdout
    assert test_case.expected_second_fragment in second.stdout


@pytest.mark.parametrize(
    "test_case",
    [
        CacheDependencyCliTestCase(
            description="stub importer creation invalidates project-rule output",
            config=('roots = ["src/pkg"]\ntests = []\ntooling = []\nselect = ["FFL105"]\n'),
            requester_path="src/pkg/orders/billing/main/calculate.py",
            requester_source="def calculate() -> None:\n    pass\n",
            dependency_path="src/pkg/__init__.pyi",
            dependency_source=(
                "from pkg.orders.billing.main.calculate import calculate as calculate\n"
            ),
            expected_first_exit_code=1,
            expected_second_exit_code=0,
            expected_first_fragment="FFL105",
            expected_second_fragment="Found 0 faults",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_stub_dependency_when_created_then_installed_cache_invalidates(
    tmp_path: Path,
    test_case: CacheDependencyCliTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=(
            ("src/pkg/__init__.py", ""),
            (test_case.requester_path, test_case.requester_source),
        ),
    )
    first: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))
    dependency: Path = tmp_path / test_case.dependency_path
    dependency.write_text(test_case.dependency_source, encoding="utf-8")

    second: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=("--cache",))

    assert first.returncode == test_case.expected_first_exit_code
    assert second.returncode == test_case.expected_second_exit_code
    assert test_case.expected_first_fragment in first.stdout
    assert test_case.expected_second_fragment in second.stdout
