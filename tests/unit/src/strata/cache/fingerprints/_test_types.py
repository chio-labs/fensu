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
class CachePreferenceFingerprintTestCase:
    """Two operational cache preferences and expected semantic identity parity."""

    description: str
    first_enabled: bool
    second_enabled: bool
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


@dataclass(frozen=True)
class FileResultFingerprintTestCase:
    """Two file results and expected correctness and integrity identities."""

    description: str
    first_global: str
    second_global: str
    first_dependency_answer: bool
    second_dependency_answer: bool
    first_fault_message: str
    second_fault_message: str
    expected_result_equal: bool
    expected_record_equal: bool


@dataclass(frozen=True)
class GlobalRuntimeFingerprintTestCase:
    """Runtime semantic identities and expected global invalidation."""

    description: str
    first_python_implementation: str
    second_python_implementation: str
    first_contract_version: int
    second_contract_version: int
    expected_equal: bool


@dataclass(frozen=True)
class GlobalFingerprintBuilderTestCase:
    """Loaded package availability and expected global builder result."""

    description: str
    package_available: bool
    source_available: bool
    complete_source: bool
    expected_available: bool


@dataclass(frozen=True)
class CustomRulesFingerprintTestCase:
    """Custom-rule file contents and expected identity sensitivity."""

    description: str
    first_helper_source: str
    second_helper_source: str
    expected_equal: bool
    expected_missing_none: bool


@dataclass(frozen=True)
class CacheBlockedRulesetTestCase:
    """One custom-rule cacheability declaration and expected disabled reason."""

    description: str
    cacheable: bool
    expected_blocked: bool
    expected_reason_fragment: str
