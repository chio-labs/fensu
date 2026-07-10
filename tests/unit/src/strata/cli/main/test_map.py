"""Tests for deterministic `strata map` output."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cli.main.map import run_map
from tests.unit.src.strata.cli.main._test_types import (
    MapCommandTestCase,
    MapPresentationTestCase,
    StandaloneMapTestCase,
)
from tests.unit.src.strata.cli.main.helpers import (
    CaptureOutput,
    configure_no_color,
    write_cli_map_project,
    write_multi_root_map_project,
)


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


@pytest.mark.parametrize(
    "test_case",
    [
        StandaloneMapTestCase(
            description="src import root is inferred without Strata configuration",
            configured_root="src/pkg",
            argv=("pkg.entry.run",),
            relative_imports=False,
            expected_output_fragments=(
                "run(...)  src/pkg/entry.py:3",
                "step(...)  src/pkg/steps.py:3",
            ),
        ),
        StandaloneMapTestCase(
            description="repository root is inferred when src is absent",
            configured_root="pkg",
            argv=("pkg.entry.run",),
            relative_imports=True,
            expected_output_fragments=(
                "run(...)  pkg/entry.py:3",
                "finish(...)  pkg/finish.py:1",
            ),
        ),
        StandaloneMapTestCase(
            description="explicit import root supports an arbitrary namespace layout",
            configured_root="backend/acme",
            argv=("acme.entry.run", "--root", "backend"),
            relative_imports=False,
            expected_output_fragments=(
                "run(...)  backend/acme/entry.py:3",
                "step(...)  backend/acme/steps.py:3",
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_repository_without_strata_config_when_mapping_then_uses_project_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: StandaloneMapTestCase,
) -> None:
    write_cli_map_project(
        root=tmp_path,
        configured_root=test_case.configured_root,
        write_config=False,
        relative_imports=test_case.relative_imports,
    )
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MapCommandTestCase(
            description="resolved and unresolved calls retain source order",
            argv=("run", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=("callback(...)", "step(...)"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_mixed_call_types_when_mapping_then_preserves_call_site_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapCommandTestCase,
) -> None:
    write_cli_map_project(root=tmp_path, dynamic_seam=True, dynamic_first=True)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert output.index(test_case.expected_output_fragments[0]) < output.index(
        test_case.expected_output_fragments[1]
    )


@pytest.mark.parametrize(
    "test_case",
    [
        MapPresentationTestCase(
            description="automatic color styles terminal output",
            argv=("run",),
            is_terminal=True,
            no_color=False,
            expected_output_fragments=("\x1b[38;5;208mrun(...)\x1b[0m", "\x1b[2m"),
            expected_absent_fragments=(),
        ),
        MapPresentationTestCase(
            description="NO_COLOR suppresses explicitly requested color",
            argv=("run", "--color", "always"),
            is_terminal=True,
            no_color=True,
            expected_output_fragments=("run(...)  src/pkg/entry.py:3",),
            expected_absent_fragments=("\x1b[",),
        ),
        MapPresentationTestCase(
            description="never color keeps redirected output plain",
            argv=("run", "--color", "never"),
            is_terminal=True,
            no_color=False,
            expected_output_fragments=("run(...)  src/pkg/entry.py:3",),
            expected_absent_fragments=("\x1b[",),
        ),
        MapPresentationTestCase(
            description="unresolved dynamic seams are yellow",
            argv=("run", "--color", "always"),
            is_terminal=False,
            no_color=False,
            expected_output_fragments=(
                "\x1b[2m│   └── \x1b[0m",
                "\x1b[33m(unresolved parameter call)\x1b[0m",
            ),
            expected_absent_fragments=(),
            dynamic_seam=True,
        ),
        MapPresentationTestCase(
            description="cycles are magenta",
            argv=("run", "--color", "always", "--depth", "5"),
            is_terminal=False,
            no_color=False,
            expected_output_fragments=("\x1b[35m  (cycle)\x1b[0m",),
            expected_absent_fragments=(),
            cycle=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_color_mode_when_mapping_then_applies_terminal_color_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapPresentationTestCase,
) -> None:
    write_cli_map_project(
        root=tmp_path,
        cycle=test_case.cycle,
        dynamic_seam=test_case.dynamic_seam,
    )
    monkeypatch.chdir(tmp_path)
    configure_no_color(monkeypatch=monkeypatch, enabled=test_case.no_color)
    stdout: CaptureOutput = CaptureOutput(is_terminal=test_case.is_terminal)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == 0
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MapCommandTestCase(
            description="absolute paths retain the complete filesystem location",
            argv=("run", "--paths", "absolute"),
            expected_exit_code=0,
            expected_output_fragments=("src/pkg/entry.py:3",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_absolute_path_mode_when_mapping_then_renders_filesystem_paths(
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
    assert str(tmp_path / test_case.expected_output_fragments[0]) in stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        MapCommandTestCase(
            description="compact paths retain ownership edges and filename",
            argv=("run", "--paths", "compact"),
            expected_exit_code=0,
            expected_output_fragments=("src/company/…/pkg/entry.py:3",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_compact_path_mode_when_mapping_then_collapses_middle_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapCommandTestCase,
) -> None:
    write_cli_map_project(root=tmp_path, configured_root="src/company/product/pkg")
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
            description="none path mode renders only call structure",
            argv=("run", "--paths", "none"),
            expected_exit_code=0,
            expected_output_fragments=("run(...)", "step(...)", "finish(...)"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_none_path_mode_when_mapping_then_omits_all_locations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapCommandTestCase,
) -> None:
    write_cli_map_project(root=tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert ".py:" not in output


@pytest.mark.parametrize(
    "test_case",
    [
        MapCommandTestCase(
            description="missing explicit root returns a clear command error",
            argv=("run", "--root", "missing"),
            expected_exit_code=2,
            expected_output_fragments=("Mapping root path does not exist: missing",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_missing_explicit_root_when_mapping_then_returns_clear_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapCommandTestCase,
) -> None:
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
            description="calls resolve across repeated explicit import roots",
            argv=(
                "acme.entry.run",
                "--root",
                "services",
                "--root",
                "libraries",
            ),
            expected_exit_code=0,
            expected_output_fragments=(
                "run(...)  services/acme/entry.py:3",
                "step(...)  libraries/shared/steps.py:1",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_multiple_import_roots_when_mapping_then_resolves_cross_root_calls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapCommandTestCase,
) -> None:
    write_multi_root_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
