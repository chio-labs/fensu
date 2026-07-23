"""Test case types for config loading and validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import RuleOptionValue


@dataclass(frozen=True)
class ConfigSourceLoadTestCase:
    """Config source files and the expected loaded values."""

    description: str
    fensu_toml: str | None
    pyproject_toml: str | None
    expected_roots: tuple[str, ...]
    expected_select: tuple[str, ...]


@dataclass(frozen=True)
class ConfigDiscoveryTestCase:
    """Config files plus a starting path and the expected source outcome."""

    description: str
    start_relative_path: str
    child_pyproject_toml: str | None
    parent_fensu_toml: str | None
    expected_roots: tuple[str, ...]


@dataclass(frozen=True)
class InvalidConfigTestCase:
    """An invalid config file and the expected error."""

    description: str
    config_text: str
    expected_error_type: type[Exception]
    expected_error_fragment: str


@dataclass(frozen=True)
class RuleSelectorConfigTestCase:
    """Configured selectors and their expected normalized values."""

    description: str
    config_text: str
    expected_select: tuple[str, ...]
    expected_warn: tuple[str, ...]
    expected_ignore: tuple[str, ...]


@dataclass(frozen=True)
class InvalidConfigSourceTestCase:
    """Invalid or missing config source and the expected error."""

    description: str
    fensu_toml: str | None
    pyproject_toml: str | None
    expected_error_type: type[Exception]
    expected_error_fragment: str


@dataclass(frozen=True)
class ConfigDefaultsTestCase:
    """A valid config file and the expected normalized config values."""

    description: str
    config_text: str
    expected_roots: tuple[str, ...]
    expected_tests: tuple[str, ...]
    expected_tooling: tuple[str, ...]
    expected_threshold_name: str
    expected_threshold_value: int
    expected_role_name: str | None
    expected_role_threshold_name: str | None
    expected_role_threshold_value: int | None


@dataclass(frozen=True)
class CacheConfigTestCase:
    """A cache preference and its expected normalized value."""

    description: str
    config_text: str
    expected_enabled: bool


@dataclass(frozen=True)
class MemoryConfigTestCase:
    """Memory preferences and their expected normalized values."""

    description: str
    config_text: str
    expected_enabled: bool
    expected_archive_after_days: int


@dataclass(frozen=True)
class EvaluationConfigTestCase:
    """Evaluation path configuration and its expected normalized values."""

    description: str
    config_text: str
    expected_include: tuple[str, ...]
    expected_exclude: tuple[str, ...]


@dataclass(frozen=True)
class SkillsConfigTestCase:
    """A persistent skill identity and its expected normalized config value."""

    description: str
    config_text: str
    expected_name: str | None


@dataclass(frozen=True)
class RuleIgnoreConfigTestCase:
    """Path-scoped rule policy and its expected normalized values."""

    description: str
    config_text: str
    expected_rules: tuple[str, ...]
    expected_paths: tuple[str, ...]
    expected_reason: str


@dataclass(frozen=True)
class ConfigListFieldTestCase:
    """A list-valued config field and the expected normalized tuple."""

    description: str
    config_text: str
    expected_field_name: str
    expected_value: tuple[str, ...]


@dataclass(frozen=True)
class ConfigThresholdTestCase:
    """Threshold override expectations."""

    description: str
    config_text: str
    expected_threshold_name: str
    expected_threshold_value: int


@dataclass(frozen=True)
class ThresholdOverrideConfigTestCase:
    """A path threshold override and its expected normalized fields."""

    description: str
    config_text: str
    expected_paths: tuple[str, ...]
    expected_threshold_name: str
    expected_threshold_value: int
    expected_reason: str


@dataclass(frozen=True)
class ThresholdResolutionTestCase:
    """Threshold layers and the expected path-aware resolution result."""

    description: str
    config_text: str
    path: str
    role: str | None
    threshold_name: str
    expected_value: int
    expected_pattern: str | None
    expected_reason: str | None = None
    expected_override_order: int | None = None


@dataclass(frozen=True)
class PathPatternTestCase:
    """A repository path glob and expected anchored match result."""

    description: str
    pattern: str
    path: str
    expected_matches: bool


@dataclass(frozen=True)
class PathPatternSpecificityTestCase:
    """A normalized path glob and its expected semantic specificity tuple."""

    description: str
    pattern: str
    expected_specificity: tuple[int, int, int, int]


@dataclass(frozen=True)
class ConfigContractTestCase:
    """Contract default and override expectations."""

    description: str
    config_text: str
    expected_pattern: str
    expected_behavior: str


@dataclass(frozen=True)
class ConfigImmutabilityTestCase:
    """A config mutation attempt and the expected exception type."""

    description: str
    config_text: str
    expected_error_type: type[Exception]


@dataclass(frozen=True)
class RuleExceptionConfigTestCase:
    """Configured rule exception and expected normalized fields."""

    description: str
    config_text: str
    expected_rule: str
    expected_path: str
    expected_symbols: tuple[str, ...]
    expected_reason: str


@dataclass(frozen=True)
class InMemoryConfigBuildTestCase:
    """A raw mapping and its expected normalized config values."""

    description: str
    raw_config: dict[str, object]
    expected_roots: tuple[str, ...]
    expected_select: tuple[str, ...]
    expected_warn: tuple[str, ...]
    expected_shared_domain_minimum: int


@dataclass(frozen=True)
class InvalidInMemoryConfigTestCase:
    """An invalid raw mapping and its expected validation error."""

    description: str
    raw_config: dict[str, object]
    expected_error_type: type[Exception]
    expected_error_fragment: str


@dataclass(frozen=True)
class MissingConfigGuidanceTestCase:
    """Expected stable prefix and actionable missing-config guidance."""

    description: str
    expected_prefix: str
    expected_guidance: str


@dataclass(frozen=True)
class RuleOptionsResolutionTestCase:
    """Raw per-rule options and their expected resolved current values."""

    description: str
    raw_config: dict[str, object]
    rules: tuple[RuleSpec, ...]
    expected_rule_options: Mapping[str, Mapping[str, RuleOptionValue]]


@dataclass(frozen=True)
class InvalidRuleOptionsConfigTestCase:
    """Invalid per-rule options and their expected deterministic error detail."""

    description: str
    raw_rule_options: dict[str, dict[str, object]]
    rules: tuple[RuleSpec, ...]
    expected_error_fragment: str


@dataclass(frozen=True)
class RuleOptionsImmutabilityTestCase:
    """Nested per-rule values and their expected defensive-copy behavior."""

    description: str
    rule_code: str
    option_name: str
    original_value: RuleOptionValue
    replacement_value: RuleOptionValue
    expected_error_type: type[Exception]


@dataclass(frozen=True)
class PublicRuleOptionsLoadTestCase:
    """A real custom rule config and its expected resolved option values."""

    description: str
    config_text: str
    rule_relative_path: str
    rule_source: str
    expected_rule_options: Mapping[str, Mapping[str, RuleOptionValue]]


@dataclass(frozen=True)
class RuleOptionsValidationOrderTestCase:
    """Malformed options and evidence that custom rule import did not execute."""

    description: str
    config_text: str
    rule_relative_path: str
    rule_source: str
    marker_relative_path: str
    expected_error_type: type[Exception]
    expected_error_fragment: str
    expected_marker_exists: bool
