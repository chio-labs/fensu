"""Test case types for ruleset registry behavior."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CustomRuleLoadTestCase:
    """Custom rule source and expected loaded rule facts."""

    description: str
    rule_code: str
    expected_code: str
    expected_source_fragment: str


@dataclass(frozen=True)
class RegistryErrorTestCase:
    """Invalid custom rule source and expected ConfigError fragment."""

    description: str
    rule_source: str
    expected_error_fragment: str


@dataclass(frozen=True)
class ModuleIsolationTestCase:
    """Foreign and loaded rule codes for module-local discovery tests."""

    description: str
    stale_rule_code: str
    loaded_rule_code: str
    expected_codes: tuple[str, ...]


@dataclass(frozen=True)
class SelectCompositionTestCase:
    """Ruleset select/ignore inputs and expected selected codes."""

    description: str
    select: tuple[str, ...]
    ignore: tuple[str, ...]
    expected_codes: tuple[str, ...]
