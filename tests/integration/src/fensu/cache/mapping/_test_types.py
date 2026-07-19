"""Test case declarations for mapping cache behavior."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MapCacheTestCase:
    """One persistent mapping-cache behavior."""

    description: str
    expected_cold_manifest_hit: bool
    expected_warm_manifest_hit: bool
    expected_warm_parsed_files: int


@dataclass(frozen=True)
class MapCacheInvalidationTestCase:
    """One source invalidation behavior."""

    description: str
    changed_source: str
    expected_reused_file_records: int
    expected_output_fragment: str
    expected_writes: int


@dataclass(frozen=True)
class MapParseParityTestCase:
    """Invalid map source and expected shared-factory parity."""

    description: str
    changed_source: bytes
    expected_error: str
    expected_direct_parse_paths: tuple[str, ...]


@dataclass(frozen=True)
class MapSourceEncodingTestCase:
    """Encoded Python source and expected cached map output."""

    description: str
    source: bytes
    expected_output_fragment: str


@dataclass(frozen=True)
class MapAnalysisOwnershipTestCase:
    """Expected map behavior without full analysis construction."""

    description: str
    expected_output_fragment: str
    expected_analysis_build_count: int


@dataclass(frozen=True)
class MapCacheSerializationTestCase:
    """One strict declaration decoding behavior."""

    description: str
    payload: object
    expected_valid: bool


@dataclass(frozen=True)
class MappingIdentityTestCase:
    """One changed map implementation identity component."""

    description: str
    field_name: str
    changed_value: str | int
    expected_identity_changed: bool


@dataclass(frozen=True)
class RecordIntegrityTestCase:
    """One semantic record mutation that must fail integrity validation."""

    description: str
    field_name: str
    changed_value: object
    expected_valid: bool


@dataclass(frozen=True)
class ManifestAdversarialTestCase:
    """One integrity-valid but semantically invalid manifest mutation."""

    description: str
    mutation: str
    expected_manifest_hit: bool
    expected_reused_file_records: int


@dataclass(frozen=True)
class PathSelectorParityTestCase:
    """One cached and uncached path selector spelling."""

    description: str
    absolute: bool
    expected_output_fragment: str


@dataclass(frozen=True)
class MapNoCacheTestCase:
    """One cache-disable CLI behavior."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_cache_exists: bool


@dataclass(frozen=True)
class ConcurrentRetentionTestCase:
    """One concurrent generation retention behavior."""

    description: str
    expected_reused_file_records: int
    expected_publication_writes: int
    expected_file_record_count: int


@dataclass(frozen=True)
class ExplicitRootCachePreferenceTestCase:
    """One explicit-root cache preference and override behavior."""

    description: str
    invocation_subdirectory: str
    cache_override: bool
    expected_cache_exists: bool


@dataclass(frozen=True)
class MappingIdentityFailureTestCase:
    """One mapping identity failure degradation behavior."""

    description: str
    invalid_source: bool
    expected_internal_error: bool
    expected_output_fragment: str


@dataclass(frozen=True)
class InvalidExplicitRootConfigTestCase:
    """One malformed-config explicit-root behavior."""

    description: str
    invocation_subdirectory: str
    no_cache: bool
    expected_cache_exists: bool
