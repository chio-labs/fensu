"""Installed two-package native execution acceptance tests."""

from __future__ import annotations

import os
import shutil
import subprocess
from importlib import metadata
from pathlib import Path

import pytest

from tests.e2e.src.fensu.cli.main._test_types import (
    CliProjectFile,
    DistributionOwnershipTestCase,
    NativeProcessAccountingTestCase,
    UpgradeSafetyTestCase,
)
from tests.e2e.src.fensu.cli.main.helpers import (
    exec_trace_lines,
    installed_fensu_executable,
    isolated_site_packages,
    native_exec_trace,
    write_cli_project,
)


@pytest.mark.skipif(
    os.name != "posix" or shutil.which("strace") is None,
    reason="Linux-compatible strace is required for exec accounting",
)
@pytest.mark.parametrize(
    "test_case",
    [
        NativeProcessAccountingTestCase(
            description="core-only check executes one binary and no interpreter",
            config='roots = ["src/pkg"]\ntests = []\nselect = ["FFA101"]\n',
            files=(CliProjectFile(relative_path="src/pkg/models.py", source="VALUE: int = 1\n"),),
            argv=("check", "--no-cache", "--no-color"),
            expected_exit_code=0,
            expected_exec_count=1,
        ),
        NativeProcessAccountingTestCase(
            description="memory schema executes one binary and no interpreter",
            config=('roots = ["src/pkg"]\ntests = []\n[experimental]\nmemory = true\n'),
            files=(),
            argv=("memory", "schema", "--color", "never"),
            expected_exit_code=0,
            expected_exec_count=1,
        ),
        NativeProcessAccountingTestCase(
            description="uncached map executes one binary and no interpreter",
            config='roots = ["src/pkg"]\ntests = []\n',
            files=(
                CliProjectFile(
                    relative_path="src/pkg/entry.py",
                    source="def run() -> None:\n    return None\n",
                ),
            ),
            argv=("map", "pkg.entry.run", "--no-cache", "--color", "never"),
            expected_exit_code=0,
            expected_exec_count=1,
        ),
        NativeProcessAccountingTestCase(
            description="cached map executes one binary and no interpreter",
            config='roots = ["src/pkg"]\ntests = []\n',
            files=(
                CliProjectFile(
                    relative_path="src/pkg/entry.py",
                    source="def run() -> None:\n    return None\n",
                ),
            ),
            argv=("map", "pkg.entry.run", "--cache", "--color", "never"),
            expected_exit_code=0,
            expected_exec_count=1,
        ),
        NativeProcessAccountingTestCase(
            description="skills help executes one binary and no interpreter",
            config='roots = ["src/pkg"]\ntests = []\n',
            files=(),
            argv=("skills", "--help"),
            expected_exit_code=0,
            expected_exec_count=1,
        ),
        NativeProcessAccountingTestCase(
            description="built-in skills update executes one binary and no interpreter",
            config='roots = ["src/pkg"]\ntests = []\n[skills]\nname = "fixture"\n',
            files=(CliProjectFile(relative_path="src/pkg/__init__.py", source=""),),
            argv=("skills", "--target", "agents"),
            expected_exit_code=0,
            expected_exec_count=1,
        ),
        NativeProcessAccountingTestCase(
            description="built-in skills check executes one binary and no interpreter",
            config='roots = ["src/pkg"]\ntests = []\n[skills]\nname = "fixture"\n',
            files=(CliProjectFile(relative_path="src/pkg/__init__.py", source=""),),
            argv=("skills", "--target", "agents", "--check"),
            expected_exit_code=1,
            expected_exec_count=1,
        ),
        NativeProcessAccountingTestCase(
            description="project bundle synchronization executes one binary and no interpreter",
            config='roots = ["src/pkg"]\ntests = []\n[skills]\nname = "fixture"\n',
            files=(
                CliProjectFile(relative_path="src/pkg/__init__.py", source=""),
                CliProjectFile(
                    relative_path=".ai/knowledge/repo/skills/alpha/SKILL.md",
                    source="# Alpha\n",
                ),
            ),
            argv=("skills", "--target", "agents"),
            expected_exit_code=0,
            expected_exec_count=1,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_native_command_when_running_then_no_interpreter_is_executed(
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
        argv=test_case.argv,
        trace_path=trace_path,
    )
    exec_lines: tuple[str, ...] = exec_trace_lines(trace_path)

    assert completed.returncode == test_case.expected_exit_code
    assert len(exec_lines) == test_case.expected_exec_count
    assert all("python" not in line.lower() for line in exec_lines)


@pytest.mark.skipif(
    os.name != "posix" or shutil.which("strace") is None,
    reason="Linux-compatible strace is required for exec accounting",
)
@pytest.mark.parametrize(
    "test_case",
    [
        NativeProcessAccountingTestCase(
            description="init skills and stale core check each execute one native process",
            config="",
            files=(),
            argv=("init", "--yes", "--name", "native_app", "--skills"),
            expected_exit_code=0,
            expected_exec_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_init_skills_and_stale_core_check_when_tracing_then_each_uses_one_native_process(
    tmp_path: Path,
    test_case: NativeProcessAccountingTestCase,
) -> None:
    init_root: Path = tmp_path / "init"
    init_root.mkdir()
    init_trace: Path = tmp_path / "init.trace"
    initialized: subprocess.CompletedProcess[str] = native_exec_trace(
        root=init_root,
        argv=test_case.argv,
        trace_path=init_trace,
    )
    init_execs: tuple[str, ...] = exec_trace_lines(init_trace)

    assert initialized.returncode == test_case.expected_exit_code
    assert len(init_execs) == test_case.expected_exec_count
    assert all("python" not in line.lower() for line in init_execs)

    check_root: Path = tmp_path / "check"
    check_root.mkdir()
    write_cli_project(
        root=check_root,
        config=(
            'roots = ["src/pkg"]\ntests = []\nselect = ["FFA101"]\n[skills]\nname = "fixture"\n'
        ),
        files=(("src/pkg/models.py", "VALUE: int = 1\n"),),
    )
    installed: subprocess.CompletedProcess[str] = subprocess.run(
        (str(installed_fensu_executable()), "skills", "--target", "agents"),
        cwd=check_root,
        capture_output=True,
        text=True,
        check=False,
    )
    (check_root / "fensu.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\nselect = ["FFA101"]\n[experimental]\nmemory = true\n[skills]\nname = "fixture"\n',
        encoding="utf-8",
    )
    check_trace: Path = tmp_path / "check.trace"
    checked: subprocess.CompletedProcess[str] = native_exec_trace(
        root=check_root,
        argv=("check", "--no-cache", "--no-color"),
        trace_path=check_trace,
    )
    check_execs: tuple[str, ...] = exec_trace_lines(check_trace)

    assert installed.returncode == 0
    assert checked.returncode == test_case.expected_exit_code
    assert "Fensu skill files are out of date" in checked.stderr
    assert len(check_execs) == test_case.expected_exec_count
    assert all("python" not in line.lower() for line in check_execs)


@pytest.mark.skipif(
    os.name != "posix" or shutil.which("strace") is None,
    reason="Linux-compatible strace is required for exec accounting",
)
@pytest.mark.parametrize(
    "test_case",
    [
        NativeProcessAccountingTestCase(
            description="custom skills executes one binary and exactly one Python metadata host",
            config=(
                'roots = ["src/pkg"]\ntests = []\nselect = ["XSK001"]\n'
                'rule_paths = ["rules/custom.py"]\n[skills]\nname = "fixture"\n'
            ),
            files=(
                CliProjectFile(relative_path="src/pkg/target.py", source="VALUE: int = 1\n"),
                CliProjectFile(
                    relative_path="rules/custom.py",
                    source=(
                        "import ast\n"
                        "from fensu import Family, Fault, RuleContext, rule\n\n"
                        '@rule(code="XSK001", family=Family.CUSTOM, slug="always", '
                        'message="custom fault")\n'
                        "def always(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
                        "    return [ctx.fault(node=module.body[0])]\n"
                    ),
                ),
            ),
            argv=("skills", "--target", "agents"),
            expected_exit_code=0,
            expected_exec_count=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_custom_rules_when_tracing_skills_then_launches_exactly_one_metadata_host(
    tmp_path: Path,
    test_case: NativeProcessAccountingTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=tuple((file.relative_path, file.source) for file in test_case.files),
    )
    trace_path: Path = tmp_path / "custom-skills.trace"

    completed: subprocess.CompletedProcess[str] = native_exec_trace(
        root=tmp_path,
        argv=test_case.argv,
        trace_path=trace_path,
    )
    exec_lines: tuple[str, ...] = exec_trace_lines(trace_path)

    assert completed.returncode == test_case.expected_exit_code
    assert len(exec_lines) == test_case.expected_exec_count
    assert sum("python" in line.lower() for line in exec_lines) == 1


@pytest.mark.skipif(
    os.name != "posix" or shutil.which("strace") is None,
    reason="Linux-compatible strace is required for exec accounting",
)
@pytest.mark.parametrize(
    "test_case",
    [
        NativeProcessAccountingTestCase(
            description="custom check executes one binary and exactly one Python callback host",
            config=(
                'roots = ["src/pkg"]\ntests = []\nselect = ["XCK001"]\n'
                'rule_paths = ["rules/custom.py"]\n'
            ),
            files=(
                CliProjectFile(relative_path="src/pkg/target.py", source="VALUE: int = 1\n"),
                CliProjectFile(
                    relative_path="rules/custom.py",
                    source=(
                        "import ast\n"
                        "from fensu import Family, Fault, RuleContext, rule\n\n"
                        '@rule(code="XCK001", family=Family.CUSTOM, slug="always", '
                        'message="custom fault")\n'
                        "def always(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
                        "    return [ctx.fault(node=module.body[0])]\n"
                    ),
                ),
            ),
            argv=("check", "--no-cache", "--no-color"),
            expected_exit_code=1,
            expected_exec_count=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_custom_rules_when_tracing_check_then_launches_exactly_one_callback_host(
    tmp_path: Path,
    test_case: NativeProcessAccountingTestCase,
) -> None:
    write_cli_project(
        root=tmp_path,
        config=test_case.config,
        files=tuple((file.relative_path, file.source) for file in test_case.files),
    )
    trace_path: Path = tmp_path / "custom-check.trace"

    completed: subprocess.CompletedProcess[str] = native_exec_trace(
        root=tmp_path,
        argv=test_case.argv,
        trace_path=trace_path,
    )
    exec_lines: tuple[str, ...] = exec_trace_lines(trace_path)

    assert completed.returncode == test_case.expected_exit_code
    assert "XCK001" in completed.stdout
    assert len(exec_lines) == test_case.expected_exec_count
    assert sum("python" in line.lower() for line in exec_lines) == 1


@pytest.mark.parametrize(
    "test_case",
    [
        DistributionOwnershipTestCase(
            description="CLI package exclusively owns the native script",
            expected_cli_script_name=installed_fensu_executable().name,
            expected_authoring_entrypoint_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_installed_distributions_when_inspecting_files_then_script_has_one_owner(
    test_case: DistributionOwnershipTestCase,
) -> None:
    cli_files: tuple[str, ...] = tuple(
        str(path) for path in metadata.distribution("fensu-cli").files or ()
    )
    authoring_entrypoints: tuple[metadata.EntryPoint, ...] = tuple(
        metadata.distribution("fensu").entry_points
    )

    assert any(Path(path).name == test_case.expected_cli_script_name for path in cli_files)
    assert len(authoring_entrypoints) == test_case.expected_authoring_entrypoint_count


@pytest.mark.parametrize(
    "test_case",
    [
        UpgradeSafetyTestCase(
            description="mismatched Python and binary distributions fail handshake",
            installed_version="9.9.9",
            expected_exit_code=2,
            expected_error_fragment="does not match installed fensu 9.9.9",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_mixed_upgrade_versions_when_delegating_then_handshake_rejects_environment(
    tmp_path: Path,
    test_case: UpgradeSafetyTestCase,
) -> None:
    prefix: Path = tmp_path / "environment"
    installed_binary: Path = installed_fensu_executable()
    binary: Path = prefix / installed_binary.parent.name / installed_binary.name
    binary.parent.mkdir(parents=True)
    shutil.copy2(installed_binary, binary)
    dist_info: Path = (
        isolated_site_packages(prefix) / f"fensu-{test_case.installed_version}.dist-info"
    )
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text(
        f"Metadata-Version: 2.4\nName: fensu\nVersion: {test_case.installed_version}\n",
        encoding="utf-8",
    )
    project: Path = tmp_path / "project"
    project.mkdir()
    (project / "fensu.toml").write_text(
        'roots = ["src/pkg"]\nrule_paths = ["rules/custom.py"]\n',
        encoding="utf-8",
    )

    completed: subprocess.CompletedProcess[str] = subprocess.run(
        (str(binary), "check"),
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == test_case.expected_exit_code
    assert test_case.expected_error_fragment in completed.stderr
