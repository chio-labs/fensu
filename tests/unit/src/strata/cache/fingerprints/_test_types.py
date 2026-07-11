"""Test case types for persistent cache fingerprints."""

from dataclasses import dataclass

from strata.cache.fingerprints.types import CanonicalValue


@dataclass(frozen=True)
class CanonicalFingerprintTestCase:
    """Two canonical values and whether their fingerprints must match."""

    description: str
    first: CanonicalValue
    second: CanonicalValue
    expected_equal: bool


@dataclass(frozen=True)
class ConfigFingerprintTestCase:
    """Two threshold values and whether config fingerprints must match."""

    description: str
    first_threshold: int
    second_threshold: int
    reverse_mapping_order: bool
    expected_equal: bool


@dataclass(frozen=True)
class ConfigLayoutFingerprintTestCase:
    """Two configured layouts and whether their fingerprints must match."""

    description: str
    first_roots: tuple[str, ...]
    second_roots: tuple[str, ...]
    first_tests: tuple[str, ...]
    second_tests: tuple[str, ...]
    first_tooling: tuple[str, ...]
    second_tooling: tuple[str, ...]
    expected_equal: bool


@dataclass(frozen=True)
class SourceFingerprintTestCase:
    """Two source payloads and whether their fingerprints must match."""

    description: str
    first: bytes
    second: bytes
    expected_equal: bool


@dataclass(frozen=True)
class ImplementationFingerprintTestCase:
    """Two implementation contents and whether their fingerprints must match."""

    description: str
    first: str
    second: str
    expected_equal: bool


@dataclass(frozen=True)
class RulesetFingerprintTestCase:
    """Two rule messages and whether their ruleset identities must match."""

    description: str
    first_message: str
    second_message: str
    expected_equal: bool


@dataclass(frozen=True)
class GlobalFingerprintTestCase:
    """Two Strata versions and whether their global identities must match."""

    description: str
    first_version: str
    second_version: str
    expected_equal: bool
