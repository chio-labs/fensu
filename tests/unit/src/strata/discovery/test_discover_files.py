"""Tests for discovering configured Python files."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.config.exceptions import ConfigError
from strata.discovery.exceptions import RepoRootNotFoundError
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import DiscoveredTree, ScopedFile
from tests.unit.src.strata.discovery._test_types import (
    AbsoluteRootDiscoveryTestCase,
    DiscoveryFilesTestCase,
    LayoutConfigErrorTestCase,
    MissingRootTestCase,
    ScopedRelativePartsTestCase,
)
from tests.unit.src.strata.discovery.helpers import (
    layout_error_config,
    make_config,
    relative_file_names,
    write_python_files,
)


@pytest.mark.parametrize(
    "test_case",
    [
        DiscoveryFilesTestCase(
            description="single root discovers only scoped python files",
            roots=("src/pkg",),
            tests=(),
            tooling=(),
            files=("src/pkg/domain/core/models.py", "outside.py", "src/pkg/readme.txt"),
            expected_relative_files=("src/pkg/domain/core/models.py",),
        ),
        DiscoveryFilesTestCase(
            description="file outside all scopes is skipped",
            roots=("src/pkg",),
            tests=(),
            tooling=(),
            files=("src/pkg/domain/core/models.py", "scripts/tool.py"),
            expected_relative_files=("src/pkg/domain/core/models.py",),
        ),
        DiscoveryFilesTestCase(
            description="multiple roots are discovered independently",
            roots=("src/pkg_a", "plugins/pkg_b"),
            tests=(),
            tooling=(),
            files=("src/pkg_a/domain/a.py", "plugins/pkg_b/domain/b.py"),
            expected_relative_files=("plugins/pkg_b/domain/b.py", "src/pkg_a/domain/a.py"),
        ),
        DiscoveryFilesTestCase(
            description="tests and tooling scopes are included when configured",
            roots=("src/pkg",),
            tests=("tests",),
            tooling=("scripts",),
            files=("src/pkg/domain/a.py", "tests/unit/test_a.py", "scripts/check.py"),
            expected_relative_files=(
                "scripts/check.py",
                "src/pkg/domain/a.py",
                "tests/unit/test_a.py",
            ),
        ),
        DiscoveryFilesTestCase(
            description="missing optional test and tooling scopes are ignored",
            roots=("src/pkg",),
            tests=("missing_tests",),
            tooling=("missing_scripts",),
            files=("src/pkg/domain/a.py",),
            expected_relative_files=("src/pkg/domain/a.py",),
        ),
        DiscoveryFilesTestCase(
            description="discovered files are sorted by absolute path",
            roots=("src/pkg",),
            tests=(),
            tooling=(),
            files=("src/pkg/z.py", "src/pkg/a.py", "src/pkg/m.py"),
            expected_relative_files=("src/pkg/a.py", "src/pkg/m.py", "src/pkg/z.py"),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_configured_scopes_when_discovering_then_returns_expected_python_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: DiscoveryFilesTestCase,
) -> None:
    write_python_files(root=tmp_path, relative_paths=test_case.files)
    monkeypatch.chdir(tmp_path)

    tree: DiscoveredTree = discover_files(
        config=make_config(roots=test_case.roots, tests=test_case.tests, tooling=test_case.tooling)
    )

    assert relative_file_names(repo_root=tmp_path, files=tree.files) == (
        test_case.expected_relative_files
    )
    assert tree.repo_root.path == tmp_path


@pytest.mark.parametrize(
    "test_case",
    [
        AbsoluteRootDiscoveryTestCase(
            description="absolute configured root discovers scoped files",
            root_relative_path="src/pkg",
            files=("src/pkg/domain/core/models.py", "outside.py"),
            expected_relative_files=("src/pkg/domain/core/models.py",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_absolute_root_when_discovering_then_returns_expected_python_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: AbsoluteRootDiscoveryTestCase,
) -> None:
    write_python_files(root=tmp_path, relative_paths=test_case.files)
    monkeypatch.chdir(tmp_path)
    absolute_root: str = str(tmp_path / test_case.root_relative_path)

    tree: DiscoveredTree = discover_files(config=make_config(roots=(absolute_root,)))

    assert relative_file_names(repo_root=tmp_path, files=tree.files) == (
        test_case.expected_relative_files
    )


@pytest.mark.parametrize(
    "test_case",
    [
        ScopedRelativePartsTestCase(
            description="test scope relative parts are relative to tests root",
            roots=("src/pkg",),
            tests=("tests",),
            tooling=(),
            file_path="tests/unit/src/pkg/test_models.py",
            expected_scope="test",
            expected_root_path="tests",
            expected_relative_parts=("unit", "src", "pkg", "test_models.py"),
        ),
        ScopedRelativePartsTestCase(
            description="tooling scope relative parts are relative to tooling root",
            roots=("src/pkg",),
            tests=(),
            tooling=("scripts",),
            file_path="scripts/checkers/check.py",
            expected_scope="tooling",
            expected_root_path="scripts",
            expected_relative_parts=("checkers", "check.py"),
        ),
        ScopedRelativePartsTestCase(
            description="overlapping scopes prefer the most specific test root",
            roots=(".",),
            tests=("tests",),
            tooling=(),
            file_path="tests/unit/test_models.py",
            expected_scope="test",
            expected_root_path="tests",
            expected_relative_parts=("unit", "test_models.py"),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_non_root_or_overlapping_scope_when_discovering_then_scope_facts_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ScopedRelativePartsTestCase,
) -> None:
    write_python_files(root=tmp_path, relative_paths=(test_case.file_path,))
    (tmp_path / "src/pkg").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)

    tree: DiscoveredTree = discover_files(
        config=make_config(roots=test_case.roots, tests=test_case.tests, tooling=test_case.tooling)
    )
    scoped_file: ScopedFile = tree.files[0]

    assert scoped_file.scope == test_case.expected_scope
    assert scoped_file.root == (tmp_path / test_case.expected_root_path).resolve()
    assert scoped_file.relative_parts == test_case.expected_relative_parts


@pytest.mark.parametrize(
    "test_case",
    [
        MissingRootTestCase(
            description="nonexistent code root raises repo root error",
            roots=("src/missing",),
            expected_error_fragment="src/missing",
        ),
        MissingRootTestCase(
            description="multiple nonexistent code roots are reported together",
            roots=("src/missing_a", "src/missing_b"),
            expected_error_fragment="src/missing_a, src/missing_b",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_nonexistent_root_when_discovering_then_raises_repo_root_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MissingRootTestCase,
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RepoRootNotFoundError) as error:
        discover_files(config=make_config(roots=test_case.roots))

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        LayoutConfigErrorTestCase(
            description="one path cannot be both runtime and tooling",
            roots=("src/pkg",),
            tests=(),
            tooling=("src/pkg",),
            uses_external_root=False,
            expected_error_fragment="both roots and tooling",
        ),
        LayoutConfigErrorTestCase(
            description="runtime and tooling cannot claim the same import package",
            roots=("src/tools",),
            tests=(),
            tooling=("dev/tools",),
            uses_external_root=False,
            expected_error_fragment="same import package: tools",
        ),
        LayoutConfigErrorTestCase(
            description="runtime and tests cannot claim the same import package",
            roots=("src/qa",),
            tests=("qa",),
            tooling=(),
            uses_external_root=False,
            expected_error_fragment="Runtime and test roots must not claim",
        ),
        LayoutConfigErrorTestCase(
            description="configured roots cannot escape the repository",
            roots=(),
            tests=(),
            tooling=(),
            uses_external_root=True,
            expected_error_fragment="inside the repository",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_ambiguous_or_external_layout_when_discovering_then_reports_config_error(
    tmp_path: Path,
    test_case: LayoutConfigErrorTestCase,
) -> None:
    repo_root: Path = tmp_path / "repo"
    runtime_root: Path = repo_root / "src/pkg"
    runtime_root.mkdir(parents=True)
    (repo_root / "src/tools").mkdir(parents=True)
    (repo_root / "src/qa").mkdir(parents=True)
    (repo_root / "qa").mkdir(parents=True)
    (repo_root / "dev/tools").mkdir(parents=True)
    external_root: Path = tmp_path / "external/pkg"
    external_root.mkdir(parents=True)
    with pytest.raises(ConfigError) as error:
        discover_files(
            config=layout_error_config(test_case=test_case, external_root=external_root),
            repo_root=repo_root,
        )

    assert test_case.expected_error_fragment in str(error.value)
