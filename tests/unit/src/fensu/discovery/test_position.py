"""Tests for config-driven position facts."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.discovery._helpers.module_path import module_path
from fensu.discovery._helpers.position import (
    domain,
    in_role,
    is_entry_module,
    is_main_module,
    role_of,
    subdomain,
)
from fensu.discovery.main.discover_files import discover_files
from fensu.discovery.models import DiscoveredTree, ScopedFile
from tests.unit.src.fensu.discovery._test_types import (
    MainModuleTestCase,
    MixedOwnershipRootTestCase,
    ModulePathTestCase,
    PositionFactTestCase,
)
from tests.unit.src.fensu.discovery.helpers import make_config, only_file, write_python_files


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
            file_path="src/pkg/config/core/_helpers/parse.py",
            expected_relative_parts=("config", "core", "_helpers", "parse.py"),
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
        PositionFactTestCase(
            description="configured grouping level is excluded from domain identity",
            file_path="src/pkg/sources/orders/main/process.py",
            expected_relative_parts=("sources", "orders", "main", "process.py"),
            expected_domain="orders",
            expected_subdomain=None,
            expected_role="main",
            ownership_roots=("src/pkg/sources",),
        ),
        PositionFactTestCase(
            description="configured grouping level preserves an optional subdomain",
            file_path="src/pkg/sources/orders/importing/main/load.py",
            expected_relative_parts=(
                "sources",
                "orders",
                "importing",
                "main",
                "load.py",
            ),
            expected_domain="orders",
            expected_subdomain="importing",
            expected_role="main",
            ownership_roots=("src/pkg/sources",),
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

    tree: DiscoveredTree = discover_files(
        config=make_config(ownership_roots=test_case.ownership_roots)
    )
    scoped_file: ScopedFile = only_file(files=tree.files)

    assert scoped_file.relative_parts == test_case.expected_relative_parts
    assert domain(scoped_file) == test_case.expected_domain
    assert subdomain(scoped_file) == test_case.expected_subdomain
    assert role_of(scoped_file) == test_case.expected_role


@pytest.mark.parametrize(
    "test_case",
    [
        MixedOwnershipRootTestCase(
            description="regional sources and runtime capabilities use separate boundaries",
            ownership_roots=(
                "src/pkg/sources/*",
                "src/pkg/sources/region_a*",
                "src/pkg/runtime",
            ),
            expected_partner_owner="src/pkg/sources/region_a",
            expected_runtime_owner="src/pkg/runtime",
            expected_partner_declaration="ownership_roots[1] (src/pkg/sources/region_a*)",
            expected_runtime_declaration="ownership_roots[2] (src/pkg/runtime)",
        ),
        MixedOwnershipRootTestCase(
            description="brace selectors expand to concrete mixed-depth boundaries",
            ownership_roots=("src/pkg/{sources/*,runtime}",),
            expected_partner_owner="src/pkg/sources/region_a",
            expected_runtime_owner="src/pkg/runtime",
            expected_partner_declaration=("ownership_roots[0] (src/pkg/{sources/*,runtime})"),
            expected_runtime_declaration=("ownership_roots[0] (src/pkg/{sources/*,runtime})"),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_mixed_depth_ownership_roots_when_discovering_then_each_file_uses_its_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, test_case: MixedOwnershipRootTestCase
) -> None:
    write_python_files(
        root=tmp_path,
        relative_paths=(
            "src/pkg/sources/region_a/partner/programmes/main/load.py",
            "src/pkg/sources/region_b/inventory/main/refresh.py",
            "src/pkg/runtime/scraping/main/run.py",
            "tests/unit/src/pkg/runtime/scraping/test_run.py",
        ),
    )
    monkeypatch.chdir(tmp_path)

    tree: DiscoveredTree = discover_files(
        config=make_config(
            tests=("tests",),
            ownership_roots=test_case.ownership_roots,
        )
    )
    by_path: dict[str, ScopedFile] = {
        file.path.relative_to(tmp_path).as_posix(): file for file in tree.files
    }

    partner: ScopedFile = by_path["src/pkg/sources/region_a/partner/programmes/main/load.py"]
    runtime: ScopedFile = by_path["src/pkg/runtime/scraping/main/run.py"]
    mirrored_test: ScopedFile = by_path["tests/unit/src/pkg/runtime/scraping/test_run.py"]
    assert (domain(partner), subdomain(partner)) == ("partner", "programmes")
    assert (domain(runtime), subdomain(runtime)) == ("scraping", None)
    assert (domain(mirrored_test), subdomain(mirrored_test)) == ("scraping", None)
    assert partner.ownership_root == tmp_path / test_case.expected_partner_owner
    assert runtime.ownership_root == tmp_path / test_case.expected_runtime_owner
    assert mirrored_test.ownership_root == runtime.ownership_root
    assert partner.ownership_root_declaration == test_case.expected_partner_declaration
    assert runtime.ownership_root_declaration == test_case.expected_runtime_declaration


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
            description="main.py under main is an entry module",
            file_path="src/pkg/config/core/main/main.py",
            expected_is_entry_module=True,
            expected_is_main_module=True,
        ),
        MainModuleTestCase(
            description="nested file under main is an entry and main module",
            file_path="src/pkg/config/core/main/nested/load.py",
            expected_is_entry_module=True,
            expected_is_main_module=True,
        ),
        MainModuleTestCase(
            description="helpers file is neither entry nor main module",
            file_path="src/pkg/config/core/_helpers/parse.py",
            expected_is_entry_module=False,
            expected_is_main_module=False,
        ),
        MainModuleTestCase(
            description="main bucket nested below helpers is not an entry module",
            file_path="src/pkg/config/core/_helpers/main/read.py",
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

    tree: DiscoveredTree = discover_files(config=make_config())
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

    tree: DiscoveredTree = discover_files(config=make_config())
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
