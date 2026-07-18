"""Test case types for native-to-custom annotation parity."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NativeCustomRuleParityTestCase:
    """One native rule and source shared with its custom equivalent."""

    description: str
    native_code: str
    source: str
    expected_fault_count: int
    path: str = "src/example/main/example.py"
    scope: str = "root"
    scope_root: str | None = None


@dataclass(frozen=True)
class NativeCustomRegistryTestCase:
    """Expected gaps among native registrations, custom equivalents, and parity cases."""

    description: str
    expected_missing_codes: tuple[str, ...]
