"""Tests for deterministic project skill identity and install-root resolution."""

from pathlib import Path

import pytest

from strata.agentdocs._helpers.identity import (
    find_git_root,
    normalize_skill_identity,
    resolve_install_root,
    resolve_skill_name,
)
from strata.agentdocs.exceptions import SkillInstallError
from strata.config.exceptions import ConfigError
from strata.config.models import Config, ConfigSource, SkillsConfig
from strata.config.types import ConfigSourceKind
from tests.unit.src.strata.agentdocs._helpers._test_types import (
    GitMarkerTestCase,
    InstallRootTestCase,
    SkillNormalizationTestCase,
)
from tests.unit.src.strata.agentdocs._helpers.helpers import (
    write_git_marker,
    write_project_pyproject,
)


@pytest.mark.parametrize(
    "test_case",
    [
        SkillNormalizationTestCase(
            description="spaces underscores punctuation and repeated separators collapse",
            value=" RaceHealth__API / Worker ",
            expected_identity="racehealth-api-worker",
        ),
        SkillNormalizationTestCase(
            description="decomposable unicode is converted to stable ASCII",
            value="Crème Brûlée",
            expected_identity="creme-brulee",
        ),
        SkillNormalizationTestCase(
            description="ASCII case and digits are preserved semantically",
            value="APIv2",
            expected_identity="apiv2",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_project_name_when_normalizing_then_returns_stable_kebab_identity(
    test_case: SkillNormalizationTestCase,
) -> None:
    result: str = normalize_skill_identity(test_case.value)

    assert result == test_case.expected_identity


@pytest.mark.parametrize(
    "test_case",
    [
        SkillNormalizationTestCase(
            description="non-ASCII-only name has no safe filesystem identity",
            value="日本語",
            expected_identity="ASCII letter or digit",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_empty_ascii_identity_when_normalizing_then_raises_config_error(
    test_case: SkillNormalizationTestCase,
) -> None:
    with pytest.raises(ConfigError) as error:
        normalize_skill_identity(test_case.value)

    assert test_case.expected_identity in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        GitMarkerTestCase(
            description="ordinary Git metadata directory is accepted",
            marker_kind="directory",
            expected_found=True,
        ),
        GitMarkerTestCase(
            description="worktree or submodule Git metadata file is accepted",
            marker_kind="file",
            expected_found=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_parent_git_marker_when_discovering_then_returns_nearest_repository_root(
    tmp_path: Path, test_case: GitMarkerTestCase
) -> None:
    write_git_marker(root=tmp_path, marker_kind=test_case.marker_kind)
    project: Path = tmp_path / "apps/api"
    project.mkdir(parents=True)

    result: Path | None = find_git_root(project)

    assert (result == tmp_path) is test_case.expected_found


@pytest.mark.parametrize(
    "test_case",
    [
        InstallRootTestCase(
            description="default local root prefers discovered Git root",
            value=None,
            expected_relative_root=".",
        ),
        InstallRootTestCase(
            description="git keyword resolves the discovered Git root",
            value="git",
            expected_relative_root=".",
        ),
        InstallRootTestCase(
            description="project keyword keeps installation at config root",
            value="project",
            expected_relative_root="backend",
        ),
        InstallRootTestCase(
            description="relative explicit path resolves from invocation directory",
            value="../shared-skills",
            expected_relative_root="backend/shared-skills",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_git_project_or_path_option_when_resolving_then_returns_expected_install_root(
    tmp_path: Path, test_case: InstallRootTestCase
) -> None:
    write_git_marker(root=tmp_path, marker_kind="directory")
    project: Path = tmp_path / "backend"
    invocation: Path = project / "commands"
    invocation.mkdir(parents=True)

    result, git_root = resolve_install_root(
        value=test_case.value,
        project_root=project,
        invocation_root=invocation,
    )

    assert result.relative_to(tmp_path).as_posix() == test_case.expected_relative_root
    assert git_root == tmp_path


@pytest.mark.parametrize(
    "test_case",
    [
        InstallRootTestCase(
            description="repository without Git metadata defaults to project root",
            value=None,
            expected_relative_root="project",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_git_repository_when_resolving_default_then_falls_back_to_project_root(
    tmp_path: Path, test_case: InstallRootTestCase
) -> None:
    project: Path = tmp_path / test_case.expected_relative_root
    project.mkdir()

    result, git_root = resolve_install_root(
        value=test_case.value,
        project_root=project,
        invocation_root=project,
    )

    assert result == project
    assert git_root is None


@pytest.mark.parametrize(
    "test_case",
    [
        InstallRootTestCase(
            description="explicit Git root fails when repository metadata is absent",
            value="git",
            expected_relative_root="requires a parent Git repository",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_git_repository_when_requesting_git_root_then_raises_install_error(
    tmp_path: Path, test_case: InstallRootTestCase
) -> None:
    with pytest.raises(SkillInstallError) as error:
        resolve_install_root(
            value=test_case.value,
            project_root=tmp_path,
            invocation_root=tmp_path,
        )

    assert test_case.expected_relative_root in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        SkillNormalizationTestCase(
            description="configured name overrides nearer package and directory identities",
            value="Configured API",
            expected_identity="strata-configured-api",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_configured_identity_when_resolving_then_it_has_highest_precedence(
    tmp_path: Path, test_case: SkillNormalizationTestCase
) -> None:
    project: Path = tmp_path / "directory-name"
    write_project_pyproject(root=project, name="Package Name")
    source: ConfigSource = ConfigSource(
        path=project / "strata.toml", kind=ConfigSourceKind.STRATA_TOML
    )

    result: str = resolve_skill_name(
        config=Config(roots=("src/pkg",), skills=SkillsConfig(name=test_case.value)),
        source=source,
        project_root=project,
        git_root=tmp_path,
    )

    assert result == test_case.expected_identity


@pytest.mark.parametrize(
    "test_case",
    [
        SkillNormalizationTestCase(
            description="nearest upward project metadata beats config directory",
            value="Distribution Name",
            expected_identity="strata-distribution-name",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_upward_pyproject_when_resolving_then_uses_distribution_name(
    tmp_path: Path, test_case: SkillNormalizationTestCase
) -> None:
    write_project_pyproject(root=tmp_path, name=test_case.value)
    project: Path = tmp_path / "backend"
    project.mkdir()
    source: ConfigSource = ConfigSource(
        path=project / "strata.toml", kind=ConfigSourceKind.STRATA_TOML
    )

    result: str = resolve_skill_name(
        config=Config(roots=("src/pkg",)),
        source=source,
        project_root=project,
        git_root=tmp_path,
    )

    assert result == test_case.expected_identity


@pytest.mark.parametrize(
    "test_case",
    [
        SkillNormalizationTestCase(
            description="config directory is used when project metadata is absent",
            value="backend_api",
            expected_identity="strata-backend-api",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_explicit_or_package_name_when_resolving_then_uses_config_directory(
    tmp_path: Path, test_case: SkillNormalizationTestCase
) -> None:
    project: Path = tmp_path / test_case.value
    project.mkdir()
    source: ConfigSource = ConfigSource(
        path=project / "strata.toml", kind=ConfigSourceKind.STRATA_TOML
    )

    result: str = resolve_skill_name(
        config=Config(roots=("src/pkg",)),
        source=source,
        project_root=project,
        git_root=tmp_path,
    )

    assert result == test_case.expected_identity


@pytest.mark.parametrize(
    "test_case",
    [
        SkillNormalizationTestCase(
            description="unusable directory name falls back to Git-relative project path",
            value="日本語",
            expected_identity="strata-apps",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unusable_directory_identity_when_resolving_then_uses_git_relative_fallback(
    tmp_path: Path, test_case: SkillNormalizationTestCase
) -> None:
    project: Path = tmp_path / "apps" / test_case.value
    project.mkdir(parents=True)
    source: ConfigSource = ConfigSource(
        path=project / "strata.toml", kind=ConfigSourceKind.STRATA_TOML
    )

    result: str = resolve_skill_name(
        config=Config(roots=("src/pkg",)),
        source=source,
        project_root=project,
        git_root=tmp_path,
    )

    assert result == test_case.expected_identity


@pytest.mark.parametrize(
    "test_case",
    [
        SkillNormalizationTestCase(
            description="Strata repository defaults from its distribution metadata",
            value="stratalint",
            expected_identity="strata-stratalint",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_strata_repository_when_resolving_then_uses_stratalint_distribution_identity(
    test_case: SkillNormalizationTestCase,
) -> None:
    repository: Path = Path(__file__).resolve().parents[6]
    source: ConfigSource = ConfigSource(
        path=repository / "strata.toml",
        kind=ConfigSourceKind.STRATA_TOML,
    )

    result: str = resolve_skill_name(
        config=Config(roots=("src/strata",)),
        source=source,
        project_root=repository,
        git_root=repository,
    )

    assert result == test_case.expected_identity
