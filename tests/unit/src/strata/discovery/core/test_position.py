"""Tests for config-driven position facts."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.discovery.core.helpers.module_path import module_path
from strata.discovery.core.helpers.position import (
    domain,
    in_role,
    is_entry_module,
    is_main_module,
    role_of,
    subdomain,
)
from strata.discovery.core.main.discover_files import discover_files
from strata.discovery.core.models import DiscoveredTree, ScopedFile
from tests.unit.src.strata.discovery.core._test_types import (
    MainModuleTestCase,
    ModulePathTestCase,
    PositionFactTestCase,
)
from tests.unit.src.strata.discovery.core.helpers import make_config, only_file, write_python_files


@pytest.mark.parametrize(
    "test_case",
    [
        PositionFactTestCase(
            description="root role file is recognized for later role-placement rules",
            file_path="src/pkg/models.py",
            expected_relative_parts=("models.py",),
            expected_domain=None,
            expected_subdomain=None,
            expected_role="models",
        ),
        PositionFactTestCase(
            description="subdomain main entry has domain subdomain and main role",
            file_path="src/pkg/config/core/main/load_config.py",
            expected_relative_parts=("config", "core", "main", "load_config.py"),
            expected_domain="config",
            expected_subdomain="core",
            expected_role="main",
        ),
        PositionFactTestCase(
            description="helpers file has helper role",
            file_path="src/pkg/config/core/helpers/parse.py",
            expected_relative_parts=("config", "core", "helpers", "parse.py"),
            expected_domain="config",
            expected_subdomain="core",
            expected_role="helpers",
        ),
        PositionFactTestCase(
            description="classes file has classes role",
            file_path="src/pkg/config/core/classes/thing.py",
            expected_relative_parts=("config", "core", "classes", "thing.py"),
            expected_domain="config",
            expected_subdomain="core",
            expected_role="classes",
        ),
        PositionFactTestCase(
            description="plain module has no role",
            file_path="src/pkg/config/core/plain.py",
            expected_relative_parts=("config", "core", "plain.py"),
            expected_domain="config",
            expected_subdomain="core",
            expected_role=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_scoped_file_when_reading_position_then_returns_expected_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: PositionFactTestCase,
) -> None:
    write_python_files(root=tmp_path, relative_paths=(test_case.file_path,))
    monkeypatch.chdir(tmp_path)

    tree: DiscoveredTree = discover_files(make_config())
    scoped_file: ScopedFile = only_file(files=tree.files)

    assert scoped_file.relative_parts == test_case.expected_relative_parts
    assert domain(scoped_file) == test_case.expected_domain
    assert subdomain(scoped_file) == test_case.expected_subdomain
    assert role_of(scoped_file) == test_case.expected_role


@pytest.mark.parametrize(
    "test_case",
    [
        MainModuleTestCase(
            description="direct main file is entry and main module",
            file_path="src/pkg/config/core/main/load_config.py",
            expected_is_entry_module=True,
            expected_is_main_module=True,
        ),
        MainModuleTestCase(
            description="main package init is main but not entry",
            file_path="src/pkg/config/core/main/__init__.py",
            expected_is_entry_module=False,
            expected_is_main_module=True,
        ),
        MainModuleTestCase(
            description="main.py is not an entry module",
            file_path="src/pkg/config/core/main/main.py",
            expected_is_entry_module=False,
            expected_is_main_module=True,
        ),
        MainModuleTestCase(
            description="nested file under main is main but not entry",
            file_path="src/pkg/config/core/main/nested/load.py",
            expected_is_entry_module=False,
            expected_is_main_module=True,
        ),
        MainModuleTestCase(
            description="helpers file is neither entry nor main module",
            file_path="src/pkg/config/core/helpers/parse.py",
            expected_is_entry_module=False,
            expected_is_main_module=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_scoped_file_when_checking_main_position_then_returns_expected_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MainModuleTestCase,
) -> None:
    write_python_files(root=tmp_path, relative_paths=(test_case.file_path,))
    monkeypatch.chdir(tmp_path)

    tree: DiscoveredTree = discover_files(make_config())
    scoped_file: ScopedFile = only_file(files=tree.files)

    assert is_entry_module(scoped_file) is test_case.expected_is_entry_module
    assert is_main_module(scoped_file) is test_case.expected_is_main_module


@pytest.mark.parametrize(
    "test_case",
    [
        PositionFactTestCase(
            description="in role reports true for matching role",
            file_path="src/pkg/config/core/main/load_config.py",
            expected_relative_parts=("config", "core", "main", "load_config.py"),
            expected_domain="config",
            expected_subdomain="core",
            expected_role="main",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_scoped_file_when_checking_role_membership_then_matches_expected_role(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: PositionFactTestCase,
) -> None:
    write_python_files(root=tmp_path, relative_paths=(test_case.file_path,))
    monkeypatch.chdir(tmp_path)

    tree: DiscoveredTree = discover_files(make_config())
    scoped_file: ScopedFile = only_file(files=tree.files)

    assert in_role(scoped_file=scoped_file, role=test_case.expected_role or "") is True


@pytest.mark.parametrize(
    "test_case",
    [
        ModulePathTestCase(
            description="regular python file maps to dotted path",
            file_path="src/pkg/config/core/main/load_config.py",
            expected_module_path="config.core.main.load_config",
        ),
        ModulePathTestCase(
            description="init file maps to package path",
            file_path="src/pkg/config/core/main/__init__.py",
            expected_module_path="config.core.main",
        ),
        ModulePathTestCase(
            description="scope root init maps to empty relative module path",
            file_path="src/pkg/__init__.py",
            expected_module_path="",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_python_file_when_resolving_module_path_then_returns_expected_dotted_path(
    tmp_path: Path,
    test_case: ModulePathTestCase,
) -> None:
    path: Path = tmp_path / test_case.file_path
    root: Path = tmp_path / "src/pkg"
    write_python_files(root=tmp_path, relative_paths=(test_case.file_path,))

    result: str = module_path(path=path, root=root)

    assert result == test_case.expected_module_path
