"""Tests for validated transactional initialization execution."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from strata.config.exceptions import ConfigError
from strata.config.models import Config
from strata.scaffolding.exceptions import InitError
from strata.scaffolding.helpers.execution import build_rendered_config, execute_init_plan
from strata.scaffolding.models import InitExecution, InitPlan
from strata.scaffolding.types import AdoptionMode
from tests.unit.src.strata.scaffolding._test_types import (
    AtomicRaceTestCase,
    ConfigPathRefusalTestCase,
    ExecutionFailureTestCase,
    ExecutionTestCase,
    PostPublicationCleanupTestCase,
    PrePublicationCleanupTestCase,
    ScaffoldSymlinkTestCase,
    ScopeSymlinkTestCase,
)
from tests.unit.src.strata.scaffolding.helpers import (
    absent_paths,
    atomic_link_racer,
    build_repository,
    config_destination_kind,
    config_destination_value,
    config_temp_paths,
    fail_atomic_link,
    file_paths,
    lexisting_paths,
    prepare_config_path,
    prepare_execution_failure,
    prepare_scaffold_symlink,
    prepare_scope_python_symlink,
    present_paths,
    symlink_paths,
    temp_aliases_config,
    temp_unlink_failure,
)


@pytest.mark.parametrize(
    "test_case",
    [
        ExecutionTestCase(
            description="empty repository creates exact scaffold and full config",
            project_name="my_repo",
            expected_created_paths=("src/my_repo/__init__.py", "tests/.gitkeep"),
            expected_config_text='roots = ["src/my_repo"]\ntests = ["tests"]\nselect = ["SF"]\n',
        )
    ],
    ids=lambda case: case.description,
)
def test_given_empty_repository_plan_when_executing_then_creates_exact_roundtrippable_scaffold(
    test_case: ExecutionTestCase, tmp_path: Path
) -> None:
    plan: InitPlan = InitPlan(
        roots=(f"src/{test_case.project_name}",),
        tests=("tests",),
        tooling=(),
        adoption=AdoptionMode.FULL,
        project_name=test_case.project_name,
    )

    config: Config
    execution: InitExecution
    config, execution = execute_init_plan(repository=tmp_path, plan=plan)
    written_text: str = (tmp_path / "strata.toml").read_text(encoding="utf-8")
    roundtripped: Config = build_rendered_config(text=written_text)

    assert execution.created_paths == test_case.expected_created_paths
    assert written_text == test_case.expected_config_text
    assert (
        file_paths(root=tmp_path, paths=test_case.expected_created_paths)
        == test_case.expected_created_paths
    )
    assert roundtripped == config


@pytest.mark.parametrize(
    "test_case",
    [
        ExecutionFailureTestCase(
            description="invalid existing layout refuses before writing config",
            project_name=None,
            roots=("missing/pkg",),
            blocking_directory=None,
            expected_error_type=ConfigError,
            expected_absent_paths=("strata.toml",),
            expected_preserved_paths=(),
        ),
        ExecutionFailureTestCase(
            description="scaffold file collision rolls back newly created source tree",
            project_name="pkg",
            roots=("src/pkg",),
            blocking_directory="tests/.gitkeep",
            expected_error_type=InitError,
            expected_absent_paths=("strata.toml", "src/pkg/__init__.py", "src/pkg", "src"),
            expected_preserved_paths=("tests", "tests/.gitkeep"),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_unsafe_plan_when_executing_then_refuses_without_partial_files(
    test_case: ExecutionFailureTestCase, tmp_path: Path
) -> None:
    prepare_execution_failure(root=tmp_path, test_case=test_case)
    plan: InitPlan = InitPlan(
        roots=test_case.roots,
        tests=("tests",),
        tooling=(),
        adoption=AdoptionMode.FULL,
        project_name=test_case.project_name,
    )

    with pytest.raises(test_case.expected_error_type):
        execute_init_plan(repository=tmp_path, plan=plan)

    assert (
        absent_paths(root=tmp_path, paths=test_case.expected_absent_paths)
        == test_case.expected_absent_paths
    )
    assert (
        present_paths(root=tmp_path, paths=test_case.expected_preserved_paths)
        == test_case.expected_preserved_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigPathRefusalTestCase(
            description="regular config destination is never replaced or staged",
            path_kind="regular",
            expected_error_type=InitError,
            expected_error_fragment="Refusing to replace existing configuration path",
            expected_temp_paths=(),
        ),
        ConfigPathRefusalTestCase(
            description="broken config symlink is never replaced or staged",
            path_kind="broken-symlink",
            expected_error_type=InitError,
            expected_error_fragment="Refusing to replace existing configuration path",
            expected_temp_paths=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_existing_config_path_when_executing_then_refuses_before_atomic_staging(
    test_case: ConfigPathRefusalTestCase, tmp_path: Path
) -> None:
    build_repository(root=tmp_path, files=(("src/pkg/__init__.py", ""),))
    prepare_config_path(root=tmp_path, path_kind=test_case.path_kind)
    plan: InitPlan = InitPlan(
        roots=("src/pkg",), tests=("tests",), tooling=(), adoption=AdoptionMode.FULL
    )

    with pytest.raises(test_case.expected_error_type) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert config_temp_paths(root=tmp_path) == test_case.expected_temp_paths
    assert lexisting_paths(root=tmp_path, paths=("strata.toml",)) == ("strata.toml",)


@pytest.mark.parametrize(
    "test_case",
    [
        AtomicRaceTestCase(
            description="concurrent regular config is never overwritten",
            destination_kind="regular",
            expected_error_type=InitError,
            expected_error_fragment="created concurrently",
            expected_temp_paths=(),
            expected_destination_kind="regular",
            expected_destination_value="racing config\n",
        ),
        AtomicRaceTestCase(
            description="concurrent config symlink is never overwritten",
            destination_kind="symlink",
            expected_error_type=InitError,
            expected_error_fragment="created concurrently",
            expected_temp_paths=(),
            expected_destination_kind="symlink",
            expected_destination_value="racing-target",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_racing_config_destination_when_publishing_then_never_overwrites_and_cleans_temp(
    test_case: AtomicRaceTestCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_repository(root=tmp_path, files=(("src/pkg/__init__.py", ""),))
    monkeypatch.setattr(os, "link", atomic_link_racer(destination_kind=test_case.destination_kind))
    plan: InitPlan = InitPlan(
        roots=("src/pkg",), tests=("tests",), tooling=(), adoption=AdoptionMode.FULL
    )

    with pytest.raises(test_case.expected_error_type) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert config_temp_paths(root=tmp_path) == test_case.expected_temp_paths
    assert config_destination_kind(root=tmp_path) == test_case.expected_destination_kind
    assert config_destination_value(root=tmp_path) == test_case.expected_destination_value


@pytest.mark.parametrize(
    "test_case",
    [
        PostPublicationCleanupTestCase(
            description="temp unlink failure after publication preserves successful empty scaffold",
            expected_created_paths=("src/pkg/__init__.py", "tests/.gitkeep"),
            expected_config_text='roots = ["src/pkg"]\ntests = ["tests"]\nselect = ["SF"]\n',
            expected_temp_count=1,
            expected_temp_aliases_config=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_temp_unlink_failure_after_publication_when_executing_empty_plan_then_succeeds(
    test_case: PostPublicationCleanupTestCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Path, "unlink", temp_unlink_failure(original=Path.unlink))
    plan: InitPlan = InitPlan(
        roots=("src/pkg",),
        tests=("tests",),
        tooling=(),
        adoption=AdoptionMode.FULL,
        project_name="pkg",
    )

    config: Config
    execution: InitExecution
    config, execution = execute_init_plan(repository=tmp_path, plan=plan)
    text: str = (tmp_path / "strata.toml").read_text(encoding="utf-8")
    roundtripped: Config = build_rendered_config(text=text)

    assert execution.created_paths == test_case.expected_created_paths
    assert (
        file_paths(root=tmp_path, paths=test_case.expected_created_paths)
        == test_case.expected_created_paths
    )
    assert text == test_case.expected_config_text
    assert roundtripped == config
    assert len(config_temp_paths(root=tmp_path)) == test_case.expected_temp_count
    assert temp_aliases_config(root=tmp_path) is test_case.expected_temp_aliases_config


@pytest.mark.parametrize(
    "test_case",
    [
        PrePublicationCleanupTestCase(
            description="temp unlink failure before publication remains an explicit safe failure",
            expected_error_type=OSError,
            expected_error_fragment="temporary config cleanup failed",
            expected_absent_paths=(
                "strata.toml",
                "src/pkg/__init__.py",
                "src/pkg",
                "src",
                "tests/.gitkeep",
                "tests",
            ),
            expected_temp_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_publication_and_temp_cleanup_failures_when_executing_empty_plan_then_refuses_safely(
    test_case: PrePublicationCleanupTestCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(os, "link", fail_atomic_link)
    monkeypatch.setattr(Path, "unlink", temp_unlink_failure(original=Path.unlink))
    plan: InitPlan = InitPlan(
        roots=("src/pkg",),
        tests=("tests",),
        tooling=(),
        adoption=AdoptionMode.FULL,
        project_name="pkg",
    )

    with pytest.raises(test_case.expected_error_type) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert (
        absent_paths(root=tmp_path, paths=test_case.expected_absent_paths)
        == test_case.expected_absent_paths
    )
    assert len(config_temp_paths(root=tmp_path)) == test_case.expected_temp_count


@pytest.mark.parametrize(
    "test_case",
    [
        ScaffoldSymlinkTestCase(
            description="package symlink blocks scaffold before writing outside repository",
            symlink_kind="package",
            expected_error_type=InitError,
            expected_error_fragment="Refusing to scaffold through symlink path",
            expected_absent_paths=("strata.toml", "outside/__init__.py"),
            expected_symlink_paths=("src/pkg",),
        ),
        ScaffoldSymlinkTestCase(
            description="test symlink refusal rolls back source scaffold",
            symlink_kind="tests",
            expected_error_type=InitError,
            expected_error_fragment="Refusing to scaffold through symlink path",
            expected_absent_paths=(
                "strata.toml",
                "src/pkg/__init__.py",
                "src/pkg",
                "src",
                "outside/.gitkeep",
            ),
            expected_symlink_paths=("tests",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_scaffold_symlink_when_executing_then_refuses_and_rolls_back_created_paths(
    test_case: ScaffoldSymlinkTestCase, tmp_path: Path
) -> None:
    prepare_scaffold_symlink(root=tmp_path, test_case=test_case)
    plan: InitPlan = InitPlan(
        roots=("src/pkg",),
        tests=("tests",),
        tooling=(),
        adoption=AdoptionMode.FULL,
        project_name="pkg",
    )

    with pytest.raises(test_case.expected_error_type) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert (
        absent_paths(root=tmp_path, paths=test_case.expected_absent_paths)
        == test_case.expected_absent_paths
    )
    assert (
        symlink_paths(root=tmp_path, paths=test_case.expected_symlink_paths)
        == test_case.expected_symlink_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        ScopeSymlinkTestCase(
            description="runtime scope Python symlink is rejected before config publication",
            symlink_path="src/pkg/linked.py",
            roots=("src/pkg",),
            tests=("tests",),
            tooling=(),
            expected_error_type=InitError,
            expected_error_fragment="Selected scope contains a symlinked Python path",
            expected_config_present=False,
        ),
        ScopeSymlinkTestCase(
            description="test scope Python symlink is rejected before config publication",
            symlink_path="tests/test_linked.py",
            roots=("src/pkg",),
            tests=("tests",),
            tooling=(),
            expected_error_type=InitError,
            expected_error_fragment="Selected scope contains a symlinked Python path",
            expected_config_present=False,
        ),
        ScopeSymlinkTestCase(
            description="tooling scope Python symlink is rejected before config publication",
            symlink_path="scripts/linked.py",
            roots=("src/pkg",),
            tests=("tests",),
            tooling=("scripts",),
            expected_error_type=InitError,
            expected_error_fragment="Selected scope contains a symlinked Python path",
            expected_config_present=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_selected_scope_python_symlink_when_executing_then_rejects_before_config(
    test_case: ScopeSymlinkTestCase, tmp_path: Path
) -> None:
    prepare_scope_python_symlink(root=tmp_path, test_case=test_case)
    plan: InitPlan = InitPlan(
        roots=test_case.roots,
        tests=test_case.tests,
        tooling=test_case.tooling,
        adoption=AdoptionMode.FULL,
    )

    with pytest.raises(test_case.expected_error_type) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert (tmp_path / "strata.toml").exists() is test_case.expected_config_present
