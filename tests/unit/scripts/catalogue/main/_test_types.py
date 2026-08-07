"""Catalogue generation test cases."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GenerateCatalogueTestCase:
    """One catalogue asset state and expected generation outcome."""

    description: str
    arguments: tuple[str, ...]
    initial_catalogue: bytes
    initial_native_policy: bytes
    initial_cli_defaults: bytes
    expected_exit_code: int
    expected_current: bool


@dataclass(frozen=True)
class RuleSurfaceParityTestCase:
    """Expected cross-language rule registry differences."""

    description: str
    expected_mismatches: tuple[str, ...]
