"""Installed two-package native execution acceptance tests."""

from __future__ import annotations

import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import pytest

from tests.e2e.src.strata.cli.main._test_types import (
    CliProjectFile,
    DistributionOwnershipTestCase,
    NativeCommandParityTestCase,
    NativeProcessAccountingTestCase,
    UpgradeSafetyTestCase,
)
from tests.e2e.src.strata.cli.main.helpers import (
    exec_trace_lines,
    native_exec_trace,
    run_command_parity,
    write_cli_project,
)


@pytest.mark.parametrize(
    "test_case",
    [
        NativeCommandParityTestCase(
            description="top-level help is byte-identical",
            argv=("--help",),
            config='roots = ["src/pkg"]\ntests = []\n',
            files=(),
            expected_exit_code=0,
        ),
        NativeCommandParityTestCase(
            description="version is byte-identical",
            argv=("--version",),
            config='roots = ["src/pkg"]\ntests = []\n',
            files=(),
            expected_exit_code=0,
        ),
        NativeCommandParityTestCase(
            description="rule metadata is byte-identical",
            argv=("rule", "SFA101", "--color", "never"),
            config='roots = ["src/pkg"]\ntests = []\n',
            files=(CliProjectFile(relative_path="src/pkg/__init__.py", source=""),),
            expected_exit_code=0,
        ),
        NativeCommandParityTestCase(
            description="core check diagnostic is byte-identical",
            argv=("check", "--no-cache", "--no-color"),
            config='roots = ["src/pkg"]\ntests = []\nselect = ["SFA101"]\n',
            files=(CliProjectFile(relative_path="src/pkg/models.py", source="VALUE = 1\n"),),
            expected_exit_code=1,
        ),
        NativeCommandParityTestCase(
            description="existing-config init is byte-identical",
            argv=("init", "--yes", "--no-skills"),
            config='roots = ["src/pkg"]\ntests = []\n',
            files=(),
            expected_exit_code=0,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_supported_command_when_running_python_and_binary_then_output_is_identical(
    tmp_path: Path,
    test_case: NativeCommandParityTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=tuple((file.relative_path, file.source) for file in test_case.files),
    )

    python_result, native_result = run_command_parity(root=tmp_path, argv=test_case.argv)

    assert python_result.returncode == test_case.expected_exit_code
    assert native_result.returncode == test_case.expected_exit_code
    assert native_result.stdout == python_result.stdout
    assert native_result.stderr == python_result.stderr


@pytest.mark.skipif(shutil.which("strace") is None, reason="strace is required for exec accounting")
@pytest.mark.parametrize(
    "test_case",
    [
        NativeProcessAccountingTestCase(
            description="core-only check executes one binary and no interpreter",
            config='roots = ["src/pkg"]\ntests = []\nselect = ["SFA101"]\n',
            files=(CliProjectFile(relative_path="src/pkg/models.py", source="VALUE: int = 1\n"),),
            expected_exit_code=0,
            expected_exec_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_custom_rules_when_running_check_then_no_interpreter_is_executed(
    tmp_path: Path,
    test_case: NativeProcessAccountingTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=tuple((file.relative_path, file.source) for file in test_case.files),
    )
    trace_path: Path = tmp_path / "exec.trace"

    completed: subprocess.CompletedProcess[str] = native_exec_trace(
        root=tmp_path,
        argv=("check", "--no-cache", "--no-color"),
        trace_path=trace_path,
    )
    exec_lines: tuple[str, ...] = exec_trace_lines(trace_path)

    assert completed.returncode == test_case.expected_exit_code
    assert len(exec_lines) == test_case.expected_exec_count
    assert all("python" not in line.lower() for line in exec_lines)


@pytest.mark.parametrize(
    "test_case",
    [
        DistributionOwnershipTestCase(
            description="CLI package exclusively owns the native script",
            expected_cli_script_suffix="bin/strata",
            expected_authoring_entrypoint_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_installed_distributions_when_inspecting_files_then_script_has_one_owner(
    test_case: DistributionOwnershipTestCase,
) -> None:
    cli_files: tuple[str, ...] = tuple(
        str(path) for path in metadata.distribution("stratalint-cli").files or ()
    )
    authoring_entrypoints: tuple[metadata.EntryPoint, ...] = tuple(
        metadata.distribution("stratalint").entry_points
    )

    assert any(path.endswith(test_case.expected_cli_script_suffix) for path in cli_files)
    assert len(authoring_entrypoints) == test_case.expected_authoring_entrypoint_count


@pytest.mark.parametrize(
    "test_case",
    [
        UpgradeSafetyTestCase(
            description="stale Python wrapper reports binary reinstall recovery",
            installed_version="0.19.0",
            expected_exit_code=2,
            expected_error_fragment="stale Python console script",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_pre_split_console_wrapper_when_invoked_then_stale_script_is_rejected(
    tmp_path: Path,
    test_case: UpgradeSafetyTestCase,
) -> None:
    wrapper: Path = tmp_path / "strata"
    wrapper.write_text(
        f"#!{sys.executable}\nfrom strata.cli.main.entry import main\nraise SystemExit(main())\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    completed: subprocess.CompletedProcess[str] = subprocess.run(
        (str(wrapper), "--version"),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == test_case.expected_exit_code
    assert test_case.expected_error_fragment in completed.stderr


@pytest.mark.parametrize(
    "test_case",
    [
        UpgradeSafetyTestCase(
            description="mismatched Python and binary distributions fail handshake",
            installed_version="9.9.9",
            expected_exit_code=2,
            expected_error_fragment="does not match installed stratalint 9.9.9",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_mixed_upgrade_versions_when_delegating_then_handshake_rejects_environment(
    tmp_path: Path,
    test_case: UpgradeSafetyTestCase,
) -> None:
    prefix: Path = tmp_path / "environment"
    binary: Path = prefix / "bin/strata"
    binary.parent.mkdir(parents=True)
    shutil.copy2(Path(sys.executable).with_name("strata"), binary)
    dist_info: Path = (
        prefix
        / "lib/python3.12/site-packages"
        / f"stratalint-{test_case.installed_version}.dist-info"
    )
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text(
        f"Metadata-Version: 2.4\nName: stratalint\nVersion: {test_case.installed_version}\n",
        encoding="utf-8",
    )

    completed: subprocess.CompletedProcess[str] = subprocess.run(
        (str(binary), "skills"),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == test_case.expected_exit_code
    assert test_case.expected_error_fragment in completed.stderr
