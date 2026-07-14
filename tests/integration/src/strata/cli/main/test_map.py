"""Tests for deterministic `strata map` output."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cli.main.map import run_map
from tests.integration.src.strata.cli.main._test_types import (
    MapCommandTestCase,
    MapPresentationTestCase,
    MethodMapTestCase,
    StandaloneMapTestCase,
)
from tests.integration.src.strata.cli.main.helpers import (
    CaptureOutput,
    configure_no_color,
    write_cli_map_project,
    write_cli_method_map_project,
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
            expected_output_fragments=("\x1b[1;36mrun(...)\x1b[0m", "\x1b[2m"),
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


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="downstream methods use class-qualified labels",
            argv=("methods.entry.run", "--depth", "4"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run(...)  src/methods/entry.py:22",
                "Worker.execute(...)  src/methods/workers.py:8",
                "Worker.prepare(...)  src/methods/workers.py:11",
                "Helper.finish(...)  src/methods/support.py:2",
                "Worker.create(...)  src/methods/workers.py:15",
                "Worker.class_step(...)  src/methods/workers.py:20",
                "ImportedWorker.imported_method(...)  src/methods/imported.py:2",
                "LocalWorker.local_method(...)  src/methods/entry.py:14",
            ),
        ),
        MethodMapTestCase(
            description="direct constructor receiver resolves its concrete method",
            argv=("methods.entry.direct_dispatch", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "direct_dispatch(...)  src/methods/entry.py:47",
                "Worker.prepare(...)  src/methods/workers.py:11",
            ),
        ),
        MethodMapTestCase(
            description="factory return annotation resolves the following method",
            argv=("methods.entry.factory_dispatch", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "factory_dispatch(...)  src/methods/entry.py:51",
                "Worker.execute(...)  src/methods/workers.py:8",
                "make_worker(...)  src/methods/entry.py:18",
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_concrete_method_calls_when_mapping_then_renders_qualified_downstream_tree(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="exact dotted selector resolves one same-named method",
            argv=("methods.workers.Alpha.select",),
            expected_exit_code=0,
            expected_output_fragments=("Alpha.select(...)  src/methods/workers.py:31",),
        ),
        MethodMapTestCase(
            description="path and class selector resolves one same-named method",
            argv=("src/methods/workers::Beta.select",),
            expected_exit_code=0,
            expected_output_fragments=("Beta.select(...)  src/methods/workers.py:36",),
        ),
        MethodMapTestCase(
            description="partial class selector resolves one uniquely named method",
            argv=("Worker.prepare",),
            expected_exit_code=0,
            expected_output_fragments=("Worker.prepare(...)  src/methods/workers.py:11",),
        ),
        MethodMapTestCase(
            description="partial class selector resolves without cache",
            argv=("Worker.prepare", "--no-cache"),
            expected_exit_code=0,
            expected_output_fragments=("Worker.prepare(...)  src/methods/workers.py:11",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_exact_method_selector_when_mapping_then_resolves_class_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="bare same-named method reports class-qualified choices",
            argv=("select",),
            expected_exit_code=2,
            expected_output_fragments=(
                "Ambiguous function select",
                "methods.workers.Alpha.select",
                "methods.workers.Beta.select",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_ambiguous_method_name_when_mapping_then_reports_class_qualified_selectors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stderr.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="partial class selector reports modules when duplicated",
            argv=("Alpha.select",),
            expected_exit_code=2,
            expected_output_fragments=(
                "Ambiguous function Alpha.select",
                "methods.alternate.Alpha.select",
                "methods.workers.Alpha.select",
                "path::Alpha.select",
            ),
        ),
        MethodMapTestCase(
            description="unknown partial class selector gives working forms",
            argv=("Missing.select",),
            expected_exit_code=2,
            expected_output_fragments=(
                "Unknown project function: Missing.select",
                "full dotted key",
                "path::Missing.select",
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_partial_method_selector_when_not_unique_then_reports_working_forms(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stderr.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="dynamic method seams render while external methods are omitted",
            argv=("methods.entry.run", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "protocol.execute(...)  src/methods/entry.py:31  (unresolved protocol dispatch)",
                "dynamic.parameter_method(...)  src/methods/entry.py:32  (unresolved parameter method)",
            ),
            expected_absent_fragments=("path.exists", "Path.exists"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_dynamic_and_external_receivers_when_mapping_then_renders_only_project_seams(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="method cycle uses class-qualified callable identity",
            argv=("methods.workers.Worker.cycle_one", "--depth", "4"),
            expected_exit_code=0,
            expected_output_fragments=(
                "Worker.cycle_one(...)  src/methods/workers.py:23",
                "Worker.cycle_two(...)  src/methods/workers.py:26",
                "Worker.cycle_one(...)  src/methods/workers.py:23  (cycle)",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_recursive_methods_when_mapping_then_marks_cycle_by_method_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="receiver inference uses only compatible preceding bindings",
            argv=("methods.entry.infer_order", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "infer_order(...)  src/methods/entry.py:36",
                "Worker.execute(...)  src/methods/workers.py:8",
            ),
            expected_absent_fragments=(
                "late.prepare",
                "stable.prepare",
                "invalid.execute",
                "Worker.prepare",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_receiver_rebindings_when_mapping_then_infers_conservatively_in_source_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="subscripted protocol annotation remains an unresolved dispatch seam",
            argv=("methods.generic_protocol.run_generic", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run_generic(...)  src/methods/generic_protocol.py:11",
                "runner.execute(...)  src/methods/generic_protocol.py:12  "
                "(unresolved protocol dispatch)",
            ),
            expected_absent_fragments=("GenericRunner.execute(...)",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_generic_protocol_receiver_when_mapping_then_renders_protocol_dispatch_seam(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="conditional incompatible assignment invalidates receiver inference",
            argv=("methods.inference_cases.conditional_rebind", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "conditional_rebind(...)  src/methods/inference_cases.py:5",
            ),
            expected_absent_fragments=("Worker.prepare", "worker.prepare"),
        ),
        MethodMapTestCase(
            description="assigned factory return annotation binds the concrete receiver",
            argv=("methods.inference_cases.assigned_factory", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "assigned_factory(...)  src/methods/inference_cases.py:12",
                "Worker.execute(...)  src/methods/workers.py:8",
                "make_worker(...)  src/methods/entry.py:18",
            ),
            expected_absent_fragments=("worker.execute(...)  src/methods/inference_cases.py:14",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_receiver_assignment_flow_when_mapping_then_uses_conservative_type_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="inherited declarations dispatch self calls through each concrete subclass",
            argv=("methods.inheritance.run_children", "--depth", "2"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run_children(...)  src/methods/inheritance.py:19",
                "Child.run(...)  src/methods/inheritance.py:2",
                "Child.hook(...)  src/methods/inheritance.py:10",
                "Sibling.run(...)  src/methods/inheritance.py:2",
                "Sibling.hook(...)  src/methods/inheritance.py:15",
            ),
            expected_absent_fragments=("Base.hook", "Base.run"),
        ),
        MethodMapTestCase(
            description="multiple inherited candidates remain an unresolved dynamic attribute",
            argv=("methods.inheritance.run_ambiguous", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run_ambiguous(...)  src/methods/inheritance.py:38",
                "Ambiguous().collide(...)  src/methods/inheritance.py:39  "
                "(unresolved dynamic attribute)",
            ),
            expected_absent_fragments=("Left.collide", "Right.collide"),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_inherited_method_receiver_when_mapping_then_preserves_dispatch_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="later top-level alias wins after guarded type-checking import",
            argv=("methods.type_order.run_selected", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run_selected(...)  src/methods/type_order.py:9",
                "ImportedWorker.imported_method(...)  src/methods/imported.py:2",
            ),
            expected_absent_fragments=("Alpha.imported_method", "unresolved dynamic attribute"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_type_checking_alias_before_top_level_alias_when_mapping_then_uses_lexical_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="untyped parameter shadows same-named imported project class",
            argv=("methods.parameter_collision.run_collision", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run_collision(...)  src/methods/parameter_collision.py:4",
                "Worker.execute(...)  src/methods/parameter_collision.py:5  "
                "(unresolved parameter method)",
            ),
            expected_absent_fragments=("Worker.execute(...)  src/methods/workers.py:8",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_untyped_parameter_matching_class_when_mapping_then_parameter_shadows_class(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="incompatible local assignment shadows imported module alias",
            argv=("methods.alias_shadow.run_shadowed", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=("run_shadowed(...)  src/methods/alias_shadow.py:4",),
            expected_absent_fragments=(
                "imported_call(...)  src/methods/shadow_target.py:1",
                "target.imported_call",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_import_alias_reassigned_locally_when_mapping_then_omits_imported_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="control-flow reassignment invalidates constructor-bound self attribute",
            argv=("methods.self_attribute_flow.run_owner", "--depth", "2"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run_owner(...)  src/methods/self_attribute_flow.py:16",
                "Owner.use(...)  src/methods/self_attribute_flow.py:12",
                "self.helper.finish(...)  src/methods/self_attribute_flow.py:13  "
                "(unresolved dynamic attribute)",
            ),
            expected_absent_fragments=("Helper.finish(...)  src/methods/support.py:2",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_self_attribute_reassigned_in_control_flow_when_mapping_then_omits_original_type(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="type-checking else import supplies runtime constructor alias",
            argv=("methods.type_else.run_else_selected", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run_else_selected(...)  src/methods/type_else.py:9",
                "ImportedWorker.imported_method(...)  src/methods/imported.py:2",
            ),
            expected_absent_fragments=(
                "Alpha.imported_method",
                "unresolved dynamic attribute",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_type_checking_else_alias_when_mapping_then_resolves_runtime_import(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="shadowed constructor parameter does not bind assigned receiver type",
            argv=("methods.constructor_assignment_shadow.run_constructor_shadow", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run_constructor_shadow(...)  src/methods/constructor_assignment_shadow.py:4",
            ),
            expected_absent_fragments=(
                "Worker.execute(...)  src/methods/workers.py:8",
                "receiver.execute",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_constructor_name_shadowed_by_parameter_when_assigning_then_omits_class_edge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="shadowed module factory does not bind annotated factory return type",
            argv=("methods.factory_alias_shadow.run_factory_shadow", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run_factory_shadow(...)  src/methods/factory_alias_shadow.py:4",
            ),
            expected_absent_fragments=(
                "make_worker(...)  src/methods/factory_target.py:4",
                "Worker.execute(...)  src/methods/workers.py:8",
                "worker.execute",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_factory_module_alias_shadowed_locally_when_assigning_then_omits_return_type(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="type-checking protocol alias and runtime class alias resolve by context",
            argv=("methods.type_mixed.run_mixed", "--depth", "1"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run_mixed(...)  src/methods/type_mixed.py:9",
                "receiver.execute(...)  src/methods/type_mixed.py:10  "
                "(unresolved protocol dispatch)",
                "Worker.execute(...)  src/methods/workers.py:8",
            ),
            expected_absent_fragments=(
                "RunnerProtocol.execute(...)  src/methods/entry.py:9",
                "Selected.execute(...)  src/methods/type_mixed.py:11",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_type_checking_protocol_and_runtime_class_alias_when_mapping_then_splits_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MethodMapTestCase(
            description="class attribute assignments invalidate earlier concrete annotations",
            argv=("methods.class_attribute_flow.run_attributes", "--depth", "2"),
            expected_exit_code=0,
            expected_output_fragments=(
                "run_attributes(...)  src/methods/class_attribute_flow.py:21",
                "DirectOwner.use(...)  src/methods/class_attribute_flow.py:8",
                "self.helper.finish(...)  src/methods/class_attribute_flow.py:9  "
                "(unresolved dynamic attribute)",
                "ConditionalOwner.use(...)  src/methods/class_attribute_flow.py:17",
                "self.helper.finish(...)  src/methods/class_attribute_flow.py:18  "
                "(unresolved dynamic attribute)",
            ),
            expected_absent_fragments=("Helper.finish(...)  src/methods/support.py:2",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_class_attribute_annotation_reassigned_when_mapping_then_omits_old_type(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MethodMapTestCase,
) -> None:
    write_cli_method_map_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_map(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)
