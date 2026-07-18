"""Test case types for persistent cache fingerprints."""

from dataclasses import dataclass

from strata.cache.fingerprints.types import CanonicalValue
from strata.rules.authoring.types import ExecutionOwner


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
class ContractFingerprintTestCase:
    """Two contract behaviors and expected config identity relationship."""

    description: str
    first_behavior: str
    second_behavior: str
    expected_equal: bool


@dataclass(frozen=True)
class WarningFingerprintTestCase:
    """Two warning selections and expected config identity relationship."""

    description: str
    first_warn: tuple[str, ...]
    second_warn: tuple[str, ...]
    expected_equal: bool


@dataclass(frozen=True)
class SkillsFingerprintTestCase:
    """Two persistent skill names and expected config identity relationship."""

    description: str
    first_name: str | None
    second_name: str | None
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
class ThresholdOverrideFingerprintTestCase:
    """Two override orders and whether config fingerprints must match."""

    description: str
    expected_equal: bool


@dataclass(frozen=True)
class CachePreferenceFingerprintTestCase:
    """Two operational cache preferences and expected semantic identity parity."""

    description: str
    first_enabled: bool
    second_enabled: bool
    expected_equal: bool


@dataclass(frozen=True)
class MemoryPreferenceFingerprintTestCase:
    """Two operational memory preferences and expected semantic identity parity."""

    description: str
    first_enabled: bool
    second_enabled: bool
    first_archive_after_days: int
    second_archive_after_days: int
    expected_equal: bool


@dataclass(frozen=True)
class EvaluationFingerprintTestCase:
    """Two evaluation selections and their expected global config identity."""

    description: str
    first_include: tuple[str, ...]
    second_include: tuple[str, ...]
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
class RulesetSourceReuseTestCase:
    """Rules sharing one source and expected source read count."""

    description: str
    expected_source_reads: int


@dataclass(frozen=True)
class GlobalFingerprintTestCase:
    """Two Strata versions and whether their global identities must match."""

    description: str
    first_version: str
    second_version: str
    expected_equal: bool


@dataclass(frozen=True)
class NativeBackendFingerprintTestCase:
    """Two native extension versions and whether their global identities must match."""

    description: str
    first_backend_version: str
    second_backend_version: str
    expected_equal: bool


@dataclass(frozen=True)
class WarningModeFingerprintTestCase:
    """Two warning-mode states and whether their cache identities may match."""

    description: str
    first_enabled: bool
    second_enabled: bool
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
class RulesetExecutionOwnerFingerprintTestCase:
    """Two execution owners and their expected ruleset identity relationship."""

    description: str
    first_owner: ExecutionOwner
    second_owner: ExecutionOwner
    expected_equal: bool


@dataclass(frozen=True)
class GlobalFingerprintBuilderTestCase:
    """Loaded package availability and expected global builder result."""

    description: str
    package_available: bool
    source_available: bool
    complete_source: bool
    expected_available: bool
    expected_implementation_scans: int


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
    include_core: bool
    expected_blocked: bool
    expected_reason_fragment: str
