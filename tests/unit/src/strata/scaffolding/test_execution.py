"""Tests for validated transactional initialization execution."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from strata.config.exceptions import ConfigError
from strata.config.models import Config
from strata.scaffolding._helpers import capabilities as capabilities_module
from strata.scaffolding._helpers import execution as execution_module
from strata.scaffolding._helpers import gitignore as gitignore_module
from strata.scaffolding._helpers.execution import build_rendered_config, execute_init_plan
from strata.scaffolding._helpers.gitignore import is_gitignored, plan_gitignore_update
from strata.scaffolding.constants import (
    PYTHON_GITIGNORE_LICENSE,
    PYTHON_GITIGNORE_SHA256,
    PYTHON_GITIGNORE_SOURCE,
    PYTHON_GITIGNORE_TEMPLATE,
    STRATA_GITIGNORE_BLOCK,
)
from strata.scaffolding.exceptions import InitError
from strata.scaffolding.models import GitIgnorePlan, InitExecution, InitPlan
from tests.unit.src.strata.scaffolding._test_types import (
    AtomicRaceTestCase,
    ConfigPathRefusalTestCase,
    ExecutionFailureTestCase,
    ExecutionTestCase,
    GitIgnoreExecutionTestCase,
    GitIgnoreMatcherTestCase,
    GitIgnorePlanTestCase,
    GitIgnoreUnsafeTargetTestCase,
    ParentSwapTestCase,
    PublicationFailureTestCase,
    ScaffoldModeTestCase,
    ScaffoldSymlinkTestCase,
    ScopeSymlinkTestCase,
)
from tests.unit.src.strata.scaffolding.helpers import (
    CountingFileOpener,
    FailingPublicationWriter,
    NoDirFdOpener,
    RacingExclusiveOpener,
    RacingGitIgnorePublisher,
    SwappingDirectoryOpener,
    absent_paths,
    build_repository,
    config_destination_kind,
    config_destination_value,
    config_temp_paths,
    file_paths,
    gitignore_bytes_or_none,
    gitignore_plan_desired,
    lexisting_paths,
    prepare_config_path,
    prepare_execution_failure,
    prepare_root_gitignore,
    prepare_scaffold_symlink,
    prepare_scope_python_symlink,
    prepare_unsafe_gitignore,
    present_paths,
    symlink_paths,
)

_WINDOWS_FILE_MODE: int = 0o666


@pytest.mark.parametrize(
    "test_case",
    [
        ExecutionTestCase(
            description="empty repository creates exact scaffold and full config",
            project_name="my_repo",
            expected_created_paths=("src/my_repo/__init__.py", "tests/.gitkeep"),
            expected_config_text='roots = ["src/my_repo"]\ntests = ["tests"]\nselect = ["SF"]\n',
            expected_file_mode=0o644,
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
    assert (tmp_path / ".gitignore").read_bytes() == (
        PYTHON_GITIGNORE_TEMPLATE + STRATA_GITIGNORE_BLOCK
    )
    written_paths: tuple[Path, ...] = (
        tmp_path / "src/my_repo/__init__.py",
        tmp_path / "tests/.gitkeep",
        tmp_path / "strata.toml",
        tmp_path / ".gitignore",
    )
    expected_file_mode: int = {
        False: test_case.expected_file_mode,
        True: _WINDOWS_FILE_MODE,
    }[os.name == "nt"]
    assert tuple(path.stat().st_mode & 0o777 for path in written_paths) == (
        expected_file_mode,
    ) * len(written_paths)
    assert hashlib.sha256(PYTHON_GITIGNORE_TEMPLATE).hexdigest() == (
        "b2580eab7825b9f22f790fb0edb7a6e239616e79907004adf36023c7ec4b9a4c"
    )
    assert PYTHON_GITIGNORE_SHA256 == (
        "b2580eab7825b9f22f790fb0edb7a6e239616e79907004adf36023c7ec4b9a4c"
    )
    assert PYTHON_GITIGNORE_SOURCE == (
        "https://github.com/github/gitignore/blob/"
        "576334520435382d6522f349b9d270eda1e79a25/Python.gitignore"
    )
    assert PYTHON_GITIGNORE_LICENSE == "CC0-1.0"


@pytest.mark.parametrize(
    "test_case",
    [
        ExecutionFailureTestCase(
            description="invalid existing layout refuses before writing config",
            project_name=None,
            roots=("missing/pkg",),
            blocking_directory=None,
            expected_error_type=ConfigError,
            expected_absent_paths=("strata.toml", ".gitignore"),
            expected_preserved_paths=(),
        ),
        ExecutionFailureTestCase(
            description="scaffold file collision rolls back newly created source tree",
            project_name="pkg",
            roots=("src/pkg",),
            blocking_directory="tests/.gitkeep",
            expected_error_type=InitError,
            expected_absent_paths=(
                "strata.toml",
                ".gitignore",
                "src/pkg/__init__.py",
                "src/pkg",
                "src",
            ),
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
    plan: InitPlan = InitPlan(roots=("src/pkg",), tests=("tests",), tooling=())

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
            expected_error_fragment="concurrently",
            expected_temp_paths=(),
            expected_destination_kind="regular",
            expected_destination_value="racing config\n",
        ),
        AtomicRaceTestCase(
            description="concurrent config symlink is never overwritten",
            destination_kind="symlink",
            expected_error_type=InitError,
            expected_error_fragment="concurrently",
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
    opener: RacingExclusiveOpener = RacingExclusiveOpener(
        root=tmp_path,
        destination_name="strata.toml",
        user_content=test_case.expected_destination_value.encode(),
        destination_kind=test_case.destination_kind,
        open_file=os.open,
    )
    monkeypatch.setattr(os, "open", opener)
    plan: InitPlan = InitPlan(roots=("src/pkg",), tests=("tests",), tooling=())

    with pytest.raises(test_case.expected_error_type) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert config_temp_paths(root=tmp_path) == test_case.expected_temp_paths
    assert config_destination_kind(root=tmp_path) == test_case.expected_destination_kind
    assert config_destination_value(root=tmp_path) == test_case.expected_destination_value
    assert not (tmp_path / ".gitignore").exists()


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
        ParentSwapTestCase(
            description="intermediate source swap cannot redirect scaffold outside repository",
            expected_error_fragment="Scaffold directory path is not a directory",
            expected_absent_paths=("outside/pkg/__init__.py", "strata.toml", ".gitignore"),
        )
    ],
    ids=lambda case: case.description,
)
@pytest.mark.skipif(
    not capabilities_module.supports_dir_fd_operations(),
    reason="parent-swap injection requires descriptor-relative traversal",
)
def test_given_intermediate_parent_swap_when_scaffolding_then_refuses_without_writing_outside(
    test_case: ParentSwapTestCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside: Path = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "src").mkdir()
    opener: SwappingDirectoryOpener = SwappingDirectoryOpener(
        root=tmp_path, outside=outside, open_file=os.open
    )
    monkeypatch.setattr(os, "open", opener)
    plan: InitPlan = InitPlan(
        roots=("src/pkg",),
        tests=("tests",),
        tooling=(),
        project_name="pkg",
    )

    with pytest.raises(InitError) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert (
        absent_paths(root=tmp_path, paths=test_case.expected_absent_paths)
        == test_case.expected_absent_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        ScaffoldModeTestCase(
            description="restrictive umask applies to non-executable generated files",
            umask=0o027,
            expected_file_mode=0o640,
        )
    ],
    ids=lambda case: case.description,
)
@pytest.mark.skipif(os.name == "nt", reason="umask mode semantics are POSIX-only")
def test_given_restrictive_umask_when_scaffolding_then_regular_files_are_non_executable(
    test_case: ScaffoldModeTestCase, tmp_path: Path
) -> None:
    previous_umask: int = os.umask(test_case.umask)
    try:
        plan: InitPlan = InitPlan(
            roots=("src/pkg",),
            tests=("tests",),
            tooling=(),
            project_name="pkg",
        )
        _ = execute_init_plan(repository=tmp_path, plan=plan)
    finally:
        _ = os.umask(previous_umask)

    paths: tuple[Path, ...] = (
        tmp_path / "src/pkg/__init__.py",
        tmp_path / "tests/.gitkeep",
        tmp_path / "strata.toml",
        tmp_path / ".gitignore",
    )
    assert tuple(path.stat().st_mode & 0o777 for path in paths) == (
        test_case.expected_file_mode,
    ) * len(paths)


@pytest.mark.parametrize(
    "test_case",
    [
        PublicationFailureTestCase(
            description="partial config descriptor write removes init publications",
            expected_error_fragment="direct publication write failed",
            expected_absent_paths=(
                "strata.toml",
                ".gitignore",
                "src/pkg/__init__.py",
                "src/pkg",
                "src",
                "tests/.gitkeep",
                "tests",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_config_descriptor_write_failure_when_executing_then_cleans_partial_file_and_scaffold(
    test_case: PublicationFailureTestCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writer: FailingPublicationWriter = FailingPublicationWriter(write=os.write)
    monkeypatch.setattr(execution_module, "_write_all", writer)
    plan: InitPlan = InitPlan(
        roots=("src/pkg",),
        tests=("tests",),
        tooling=(),
        project_name="pkg",
    )

    with pytest.raises(OSError) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert (
        absent_paths(root=tmp_path, paths=test_case.expected_absent_paths)
        == test_case.expected_absent_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        GitIgnoreExecutionTestCase(
            description="no-dirfd brownfield creates a missing root gitignore",
            initial=None,
            expected_gitignore=STRATA_GITIGNORE_BLOCK,
        ),
        GitIgnoreExecutionTestCase(
            description="no-dirfd brownfield appends an existing root gitignore",
            initial=b"dist/\n",
            expected_gitignore=b"dist/\n" + STRATA_GITIGNORE_BLOCK,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_no_dirfd_capability_when_executing_brownfield_then_publishes_config_and_gitignore(
    test_case: GitIgnoreExecutionTestCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_repository(root=tmp_path, files=(("src/pkg/__init__.py", ""),))
    gitignore: Path = prepare_root_gitignore(root=tmp_path, initial=test_case.initial)
    monkeypatch.setattr(capabilities_module, "supports_dir_fd_operations", lambda: False)
    monkeypatch.setattr(os, "open", NoDirFdOpener(open_file=os.open))
    plan: InitPlan = InitPlan(roots=("src/pkg",), tests=("tests",), tooling=())

    _ = execute_init_plan(repository=tmp_path, plan=plan)

    assert (tmp_path / "strata.toml").read_text(encoding="utf-8") == (
        'roots = ["src/pkg"]\ntests = ["tests"]\nselect = ["SF"]\n'
    )
    assert gitignore.read_bytes() == test_case.expected_gitignore


@pytest.mark.parametrize(
    "test_case",
    [
        ExecutionTestCase(
            description="no-dirfd greenfield creates complete scaffold and templates",
            project_name="pkg",
            expected_created_paths=("src/pkg/__init__.py", "tests/.gitkeep"),
            expected_config_text='roots = ["src/pkg"]\ntests = ["tests"]\nselect = ["SF"]\n',
            expected_file_mode=0o644,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_dirfd_capability_when_executing_greenfield_then_creates_complete_scaffold(
    test_case: ExecutionTestCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(capabilities_module, "supports_dir_fd_operations", lambda: False)
    monkeypatch.setattr(os, "open", NoDirFdOpener(open_file=os.open))
    plan: InitPlan = InitPlan(
        roots=("src/pkg",),
        tests=("tests",),
        tooling=(),
        project_name=test_case.project_name,
    )

    _, execution = execute_init_plan(repository=tmp_path, plan=plan)

    assert execution.created_paths == test_case.expected_created_paths
    assert (tmp_path / "strata.toml").read_text(encoding="utf-8") == test_case.expected_config_text
    assert (tmp_path / ".gitignore").read_bytes() == (
        PYTHON_GITIGNORE_TEMPLATE + STRATA_GITIGNORE_BLOCK
    )
    assert (
        file_paths(root=tmp_path, paths=test_case.expected_created_paths)
        == test_case.expected_created_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        ScaffoldSymlinkTestCase(
            description="no-dirfd static parent validation refuses package symlink",
            symlink_kind="package",
            expected_error_type=InitError,
            expected_error_fragment="Refusing to scaffold through symlink path",
            expected_absent_paths=("outside/__init__.py", "strata.toml", ".gitignore"),
            expected_symlink_paths=("src/pkg",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_dirfd_capability_and_symlink_parent_when_scaffolding_then_refuses_static_path(
    test_case: ScaffoldSymlinkTestCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepare_scaffold_symlink(root=tmp_path, test_case=test_case)
    monkeypatch.setattr(capabilities_module, "supports_dir_fd_operations", lambda: False)
    monkeypatch.setattr(os, "open", NoDirFdOpener(open_file=os.open))
    plan: InitPlan = InitPlan(
        roots=("src/pkg",),
        tests=("tests",),
        tooling=(),
        project_name="pkg",
    )

    with pytest.raises(test_case.expected_error_type) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert (
        absent_paths(root=tmp_path, paths=test_case.expected_absent_paths)
        == test_case.expected_absent_paths
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
    )

    with pytest.raises(test_case.expected_error_type) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert (tmp_path / "strata.toml").exists() is test_case.expected_config_present


@pytest.mark.parametrize(
    "test_case",
    [
        GitIgnorePlanTestCase(
            description="greenfield without gitignore receives pinned Python template and Strata block",
            initial=None,
            greenfield=True,
            expected_desired=PYTHON_GITIGNORE_TEMPLATE + STRATA_GITIGNORE_BLOCK,
        ),
        GitIgnorePlanTestCase(
            description="brownfield without gitignore receives only Strata block",
            initial=None,
            greenfield=False,
            expected_desired=STRATA_GITIGNORE_BLOCK,
        ),
        GitIgnorePlanTestCase(
            description="existing LF file appends normalized block",
            initial=b"dist/\n",
            greenfield=False,
            expected_desired=b"dist/\n" + STRATA_GITIGNORE_BLOCK,
        ),
        GitIgnorePlanTestCase(
            description="existing CRLF bytes remain unchanged before normalized block",
            initial=b"dist/\r\n",
            greenfield=False,
            expected_desired=b"dist/\r\n" + STRATA_GITIGNORE_BLOCK,
        ),
        GitIgnorePlanTestCase(
            description="missing final newline is inserted before normalized block",
            initial=b"dist/",
            greenfield=False,
            expected_desired=b"dist/\n" + STRATA_GITIGNORE_BLOCK,
        ),
        GitIgnorePlanTestCase(
            description="directory pattern already covers cache database",
            initial=b".strata/\r\n",
            greenfield=False,
            expected_desired=None,
        ),
        GitIgnorePlanTestCase(
            description="anchored directory pattern already covers cache database",
            initial=b"/.strata/\n",
            greenfield=False,
            expected_desired=None,
        ),
        GitIgnorePlanTestCase(
            description="glob pattern already covers cache database",
            initial=b".strata/cache/*.db\n",
            greenfield=False,
            expected_desired=None,
        ),
        GitIgnorePlanTestCase(
            description="later negation uncovers cache database and requires append",
            initial=b".strata/\n!.strata/cache/v4.db\n",
            greenfield=False,
            expected_desired=b".strata/\n!.strata/cache/v4.db\n" + STRATA_GITIGNORE_BLOCK,
        ),
        GitIgnorePlanTestCase(
            description="leading whitespace is significant and does not cover root cache",
            initial=b" .strata/\n",
            greenfield=False,
            expected_desired=b" .strata/\n" + STRATA_GITIGNORE_BLOCK,
        ),
        GitIgnorePlanTestCase(
            description="escaped leading exclamation is literal rather than a negation",
            initial=b".strata/\n\\!.strata/cache/v4.db\n",
            greenfield=False,
            expected_desired=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_root_gitignore_when_planning_cache_exclusion_then_preserves_or_appends_exact_bytes(
    tmp_path: Path,
    test_case: GitIgnorePlanTestCase,
) -> None:
    path: Path = prepare_root_gitignore(root=tmp_path, initial=test_case.initial)

    update: GitIgnorePlan | None = plan_gitignore_update(
        repository=tmp_path, greenfield=test_case.greenfield
    )

    assert gitignore_plan_desired(plan=update) == test_case.expected_desired
    assert gitignore_bytes_or_none(path=path) == test_case.initial


@pytest.mark.parametrize(
    "test_case",
    [
        GitIgnoreMatcherTestCase(
            description="leading space matches only a path whose segment has that space",
            initial=b" .strata/\n",
            relative_path=" .strata/cache/v1.db",
            expected_ignored=True,
        ),
        GitIgnoreMatcherTestCase(
            description="escaped exclamation matches a literal leading marker",
            initial=b"\\!cache/\n",
            relative_path="!cache/v1.db",
            expected_ignored=True,
        ),
        GitIgnoreMatcherTestCase(
            description="escaped hash matches a literal leading marker instead of a comment",
            initial=b"\\#cache/\n",
            relative_path="#cache/v1.db",
            expected_ignored=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_gitignore_marker_syntax_when_matching_then_treats_escaped_markers_as_literals(
    tmp_path: Path,
    test_case: GitIgnoreMatcherTestCase,
) -> None:
    _ = prepare_root_gitignore(root=tmp_path, initial=test_case.initial)

    ignored: bool = is_gitignored(
        repository=tmp_path,
        path=tmp_path / test_case.relative_path,
        is_directory=False,
    )

    assert ignored is test_case.expected_ignored


@pytest.mark.parametrize(
    "test_case",
    [
        GitIgnorePlanTestCase(
            description="covered cache uses exactly one descriptor capture and returns no plan",
            initial=b"/.strata/\n",
            greenfield=False,
            expected_desired=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_covered_cache_when_planning_then_does_not_reopen_or_publish_gitignore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: GitIgnorePlanTestCase,
) -> None:
    _ = prepare_root_gitignore(root=tmp_path, initial=test_case.initial)
    opener: CountingFileOpener = CountingFileOpener(open_file=os.open)
    monkeypatch.setattr(os, "open", opener)

    update: GitIgnorePlan | None = plan_gitignore_update(
        repository=tmp_path, greenfield=test_case.greenfield
    )

    assert gitignore_plan_desired(plan=update) == test_case.expected_desired
    assert opener.calls == 1


@pytest.mark.parametrize(
    "test_case",
    [
        GitIgnoreUnsafeTargetTestCase(
            description="symlink gitignore is refused",
            target_kind="symlink",
            expected_error_fragment="not a regular file",
        ),
        GitIgnoreUnsafeTargetTestCase(
            description="directory gitignore is refused",
            target_kind="directory",
            expected_error_fragment="not a regular file",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_unsafe_root_gitignore_when_planning_then_refuses_target(
    tmp_path: Path,
    test_case: GitIgnoreUnsafeTargetTestCase,
) -> None:
    _ = prepare_unsafe_gitignore(root=tmp_path, target_kind=test_case.target_kind)

    with pytest.raises(InitError) as error:
        plan_gitignore_update(repository=tmp_path, greenfield=False)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        GitIgnoreExecutionTestCase(
            description="brownfield without gitignore creates minimal Strata block",
            initial=None,
            expected_gitignore=STRATA_GITIGNORE_BLOCK,
        ),
        GitIgnoreExecutionTestCase(
            description="brownfield uncovered gitignore appends Strata block",
            initial=b"dist/\n",
            expected_gitignore=b"dist/\n" + STRATA_GITIGNORE_BLOCK,
        ),
        GitIgnoreExecutionTestCase(
            description="brownfield covered gitignore remains byte-for-byte unchanged",
            initial=b"# existing\r\n/.strata/\r\n",
            expected_gitignore=b"# existing\r\n/.strata/\r\n",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_brownfield_gitignore_when_executing_then_publishes_expected_cache_exclusion(
    tmp_path: Path,
    test_case: GitIgnoreExecutionTestCase,
) -> None:
    build_repository(root=tmp_path, files=(("src/pkg/__init__.py", ""),))
    path: Path = prepare_root_gitignore(root=tmp_path, initial=test_case.initial)
    plan: InitPlan = InitPlan(roots=("src/pkg",), tests=("tests",), tooling=())

    _ = execute_init_plan(repository=tmp_path, plan=plan)

    assert path.read_bytes() == test_case.expected_gitignore


@pytest.mark.parametrize(
    "test_case",
    [
        AtomicRaceTestCase(
            description="concurrent gitignore replacement is preserved and rolls back config",
            destination_kind="regular",
            expected_error_type=InitError,
            expected_error_fragment="changed concurrently",
            expected_temp_paths=(),
            expected_destination_kind="regular",
            expected_destination_value="user concurrent edit\n",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_racing_gitignore_when_publishing_then_preserves_user_edit_and_rolls_back_init(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: AtomicRaceTestCase,
) -> None:
    build_repository(root=tmp_path, files=(("src/pkg/__init__.py", ""),))
    gitignore: Path = tmp_path / ".gitignore"
    gitignore.write_text("dist/\n", encoding="utf-8")
    publisher: RacingGitIgnorePublisher = RacingGitIgnorePublisher(
        path=gitignore,
        user_content=test_case.expected_destination_value.encode(),
        publish=execution_module.publish_gitignore_update,
    )
    monkeypatch.setattr(execution_module, "publish_gitignore_update", publisher)
    plan: InitPlan = InitPlan(roots=("src/pkg",), tests=("tests",), tooling=())

    with pytest.raises(test_case.expected_error_type) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert gitignore.read_text(encoding="utf-8") == test_case.expected_destination_value
    assert not (tmp_path / "strata.toml").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        AtomicRaceTestCase(
            description="concurrent new gitignore rolls back greenfield config and scaffold",
            destination_kind="regular",
            expected_error_type=InitError,
            expected_error_fragment="created concurrently",
            expected_temp_paths=(),
            expected_destination_kind="regular",
            expected_destination_value="user greenfield ignore\n",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_racing_new_gitignore_when_publishing_then_preserves_user_file_and_rolls_back_scaffold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: AtomicRaceTestCase,
) -> None:
    opener: RacingExclusiveOpener = RacingExclusiveOpener(
        root=tmp_path,
        destination_name=".gitignore",
        user_content=test_case.expected_destination_value.encode(),
        open_file=os.open,
    )
    monkeypatch.setattr(os, "open", opener)
    plan: InitPlan = InitPlan(
        roots=("src/pkg",),
        tests=("tests",),
        tooling=(),
        project_name="pkg",
    )

    with pytest.raises(test_case.expected_error_type) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert (tmp_path / ".gitignore").read_text() == test_case.expected_destination_value
    assert not (tmp_path / "strata.toml").exists()
    assert not (tmp_path / "src").exists()
    assert not (tmp_path / "tests").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        PublicationFailureTestCase(
            description="partial new gitignore descriptor write rolls back complete init transaction",
            expected_error_fragment="direct publication write failed",
            expected_absent_paths=(
                ".gitignore",
                "strata.toml",
                "src/pkg/__init__.py",
                "src/pkg",
                "src",
                "tests/.gitkeep",
                "tests",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_new_gitignore_descriptor_write_failure_when_executing_then_cleans_partial_transaction(
    test_case: PublicationFailureTestCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writer: FailingPublicationWriter = FailingPublicationWriter(write=os.write)
    monkeypatch.setattr(gitignore_module, "_write_all", writer)
    plan: InitPlan = InitPlan(
        roots=("src/pkg",),
        tests=("tests",),
        tooling=(),
        project_name="pkg",
    )

    with pytest.raises(OSError) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert (
        absent_paths(root=tmp_path, paths=test_case.expected_absent_paths)
        == test_case.expected_absent_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        AtomicRaceTestCase(
            description="concurrent generated-file edits survive receipt-checked rollback",
            destination_kind="regular",
            expected_error_type=InitError,
            expected_error_fragment="created concurrently",
            expected_temp_paths=(),
            expected_destination_kind="regular",
            expected_destination_value="user config replacement\n",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_user_edits_to_published_files_when_later_publication_fails_then_rollback_preserves_them(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: AtomicRaceTestCase,
) -> None:
    source: Path = tmp_path / "src/pkg/__init__.py"
    test_marker: Path = tmp_path / "tests/.gitkeep"
    config: Path = tmp_path / "strata.toml"
    source_content: bytes = b"USER_SOURCE: int = 1\n"
    test_content: bytes = b"user test marker\n"
    opener: RacingExclusiveOpener = RacingExclusiveOpener(
        root=tmp_path,
        destination_name=".gitignore",
        user_content=b"user ignore\n",
        open_file=os.open,
        writes=((source, source_content), (test_marker, test_content)),
        replacements=((config, test_case.expected_destination_value.encode()),),
    )
    monkeypatch.setattr(os, "open", opener)
    plan: InitPlan = InitPlan(
        roots=("src/pkg",),
        tests=("tests",),
        tooling=(),
        project_name="pkg",
    )

    with pytest.raises(test_case.expected_error_type) as error:
        execute_init_plan(repository=tmp_path, plan=plan)

    assert test_case.expected_error_fragment in str(error.value)
    assert source.read_bytes() == source_content
    assert test_marker.read_bytes() == test_content
    assert config.read_text() == test_case.expected_destination_value
    assert (tmp_path / ".gitignore").read_text() == "user ignore\n"
