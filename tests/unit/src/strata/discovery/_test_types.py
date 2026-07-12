"""Test case types for discovery and position facts."""

from __future__ import annotations

from dataclasses import dataclass

from strata.rules.authoring.types import Family


@dataclass(frozen=True)
class DiscoveryFilesTestCase:
    """Configured paths and the expected discovered relative files."""

    description: str
    roots: tuple[str, ...]
    tests: tuple[str, ...]
    tooling: tuple[str, ...]
    files: tuple[str, ...]
    expected_relative_files: tuple[str, ...]


@dataclass(frozen=True)
class AbsoluteRootDiscoveryTestCase:
    """An absolute configured root and expected discovered files."""

    description: str
    root_relative_path: str
    files: tuple[str, ...]
    expected_relative_files: tuple[str, ...]


@dataclass(frozen=True)
class ScopedRelativePartsTestCase:
    """A non-root scope file and its expected scope-relative parts."""

    description: str
    roots: tuple[str, ...]
    tests: tuple[str, ...]
    tooling: tuple[str, ...]
    file_path: str
    expected_scope: str
    expected_root_path: str
    expected_relative_parts: tuple[str, ...]


@dataclass(frozen=True)
class PositionFactTestCase:
    """A file path and the expected position facts."""

    description: str
    file_path: str
    expected_relative_parts: tuple[str, ...]
    expected_domain: str | None
    expected_subdomain: str | None
    expected_role: str | None


@dataclass(frozen=True)
class MainModuleTestCase:
    """A file path and expected main/entry classification."""

    description: str
    file_path: str
    expected_is_entry_module: bool
    expected_is_main_module: bool


@dataclass(frozen=True)
class RoutingTestCase:
    """A scoped file and its expected routed families."""

    description: str
    scope_path: str
    scope_name: str
    expected_families: frozenset[Family]


@dataclass(frozen=True)
class ModulePathTestCase:
    """A file path and its expected importable module path."""

    description: str
    file_path: str
    expected_module_path: str


@dataclass(frozen=True)
class MissingRootTestCase:
    """Configured missing roots and the expected error fragment."""

    description: str
    roots: tuple[str, ...]
    expected_error_fragment: str


@dataclass(frozen=True)
class LayoutConfigErrorTestCase:
    """Configured scope paths expected to fail project-layout validation."""

    description: str
    roots: tuple[str, ...]
    tests: tuple[str, ...]
    tooling: tuple[str, ...]
    uses_external_root: bool
    expected_error_fragment: str
