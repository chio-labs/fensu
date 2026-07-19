"""Test case types for layer rules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LayerRuleTestCase:
    """Layer rule fixture files and expected fault facts."""

    description: str
    rule_code: str
    files: tuple[tuple[str, str], ...]
    expected_codes: tuple[str, ...]
    expected_lines: tuple[int | None, ...]
    expected_messages: tuple[str, ...] = field(default_factory=tuple)
    roots: tuple[str, ...] = ("src/pkg",)
    tests: tuple[str, ...] = ()
    tooling: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolingImportRuleTestCase:
    """Layer rule fixture with tooling scope and expected fault facts."""

    description: str
    files: tuple[tuple[str, str], ...]
    tooling: tuple[str, ...]
    expected_codes: tuple[str, ...]
    expected_lines: tuple[int | None, ...]


@dataclass(frozen=True)
class NativeLayerRegistryTestCase:
    """Expected native and dependency-sensitive Python layer registrations."""

    description: str
    expected_native_codes: tuple[str, ...]
    expected_python_codes: tuple[str, ...]


@dataclass(frozen=True)
class OwnershipClassificationTestCase:
    """Module path and expected structural ownership classification."""

    description: str
    module_parts: tuple[str, ...]
    initializer: bool
    expected_package: str | None
    expected_owner_prefix: tuple[str, ...]
    expected_domain: str | None
    expected_first_role: str | None
    expected_tail: tuple[str, ...]


@dataclass(frozen=True)
class LayoutImportConsistencyTestCase:
    """Role-endorsed layout and expected combined role/layer diagnostics."""

    description: str
    role_code: str
    files: tuple[tuple[str, str], ...]
    expected_codes: tuple[str, ...]
