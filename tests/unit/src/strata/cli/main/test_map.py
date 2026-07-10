"""Tests for deterministic `strata map` output."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cli.main.map import run_map
from tests.unit.src.strata.cli.main._test_types import MapCommandTestCase
from tests.unit.src.strata.cli.main.helpers import CaptureOutput, write_cli_map_project


@pytest.mark.parametrize(
    "test_case",
    [
        MapCommandTestCase(
            description="downstream map resolves direct imported project calls",
            argv=("run", "--depth", "3"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run(...)  src/pkg/entry.py:3",
                "└── step(...)  src/pkg/steps.py:3",
                "    └── finish(...)  src/pkg/finish.py:1",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_resolvable_function_when_mapping_then_renders_downstream_tree(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapCommandTestCase,
) -> None:
    write_cli_map_project(root=tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MapCommandTestCase(
            description="namespace package outside src resolves by configured package root",
            argv=("acme.entry.run", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run(...)  backend/acme/entry.py:3",
                "step(...)  backend/acme/steps.py:3",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_arbitrary_package_root_when_mapping_then_resolves_package_imports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapCommandTestCase,
) -> None:
    write_cli_map_project(root=tmp_path, configured_root="backend/acme")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MapCommandTestCase(
            description="depth limit is rendered instead of silently truncating",
            argv=("run", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=("step(...)  src/pkg/steps.py:3  (depth limit)",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_depth_limit_when_mapping_then_marks_truncated_branch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapCommandTestCase,
) -> None:
    write_cli_map_project(root=tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MapCommandTestCase(
            description="recursive project call is marked as a cycle",
            argv=("run", "--depth", "5"),
            expected_exit_code=0,
            expected_output_fragments=("run(...)  src/pkg/entry.py:3  (cycle)",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_recursive_call_when_mapping_then_marks_cycle_without_looping(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapCommandTestCase,
) -> None:
    write_cli_map_project(root=tmp_path, cycle=True)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MapCommandTestCase(
            description="parameter callback is rendered as an unresolved seam",
            argv=("run", "--depth", "2"),
            expected_exit_code=0,
            expected_output_fragments=(
                "callback(...)  src/pkg/entry.py:5  (unresolved parameter call)",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_parameter_call_when_mapping_then_marks_unresolved_seam(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapCommandTestCase,
) -> None:
    write_cli_map_project(root=tmp_path, dynamic_seam=True)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MapCommandTestCase(
            description="ambiguous bare function reports qualified choices",
            argv=("run",),
            expected_exit_code=2,
            expected_output_fragments=("Ambiguous function run", "pkg.entry.run", "pkg.other.run"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_ambiguous_function_when_mapping_then_returns_clear_choices(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapCommandTestCase,
) -> None:
    write_cli_map_project(root=tmp_path, ambiguous=True)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stderr.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MapCommandTestCase(
            description="dotted selector resolves one ambiguous function",
            argv=("pkg.entry.run",),
            expected_exit_code=0,
            expected_output_fragments=("run(...)  src/pkg/entry.py:3",),
        ),
        MapCommandTestCase(
            description="path selector resolves one ambiguous function",
            argv=("src/pkg/entry::run",),
            expected_exit_code=0,
            expected_output_fragments=("run(...)  src/pkg/entry.py:3",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_qualified_selector_when_mapping_then_resolves_ambiguous_function(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapCommandTestCase,
) -> None:
    write_cli_map_project(root=tmp_path, ambiguous=True)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MapCommandTestCase(
            description="invalid project Python returns a clear map error",
            argv=("run",),
            expected_exit_code=2,
            expected_output_fragments=("Could not parse", "entry.py"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_python_when_mapping_then_returns_clear_parse_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapCommandTestCase,
) -> None:
    write_cli_map_project(root=tmp_path)
    (tmp_path / "src/pkg/entry.py").write_text("def broken(:\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stderr.getvalue() for fragment in test_case.expected_output_fragments)
