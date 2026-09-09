"""Test case types for ruleset registry behavior."""

from __future__ import annotations

from dataclasses import dataclass

from fensu.config.models import RuleIgnoreEntry
from fensu.config.types import AnalyzerId


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
class DirectRuleSpecErrorTestCase:
    """Malformed direct RuleSpec metadata and its expected loading error."""

    description: str
    rule_code: object
    family_expression: str
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


@dataclass(frozen=True)
class RuleSelectionTestCase:
    """Policy selectors and expected resolved blocking, warning, and ignored codes."""

    description: str
    select: tuple[str, ...]
    warn: tuple[str, ...]
    ignore: tuple[str, ...]
    expected_blocking_codes: tuple[str, ...]
    expected_warning_codes: tuple[str, ...]
    expected_ignored_codes: tuple[str, ...]


@dataclass(frozen=True)
class RuleSelectionErrorTestCase:
    """Overlapping policy selectors and their deterministic configuration error."""

    description: str
    select: tuple[str, ...]
    warn: tuple[str, ...]
    ignore: tuple[str, ...]
    expected_error: str
    rule_ignores: tuple[RuleIgnoreEntry, ...] = ()


@dataclass(frozen=True)
class AnalyzerRuleSelectionTestCase:
    """Target analyzer policy and expected applicable rule selection."""

    description: str
    analyzer: AnalyzerId
    select: tuple[str, ...]
    expected_codes: tuple[str, ...]
    expected_error_fragment: str | None
    alias_of: str | None = None


@dataclass(frozen=True)
class CustomRuleAnalyzerTestCase:
    """Custom rule analyzer applicability and expected registration error."""

    description: str
    analyzer: AnalyzerId
    expected_error_fragment: str


@dataclass(frozen=True)
class CatalogueQualityTestCase:
    """Forbidden metadata fragments and expected catalogue-quality result."""

    description: str
    forbidden_message_fragments: tuple[str, ...]
    max_message_length: int
    max_remediation_length: int
    expected_issues: tuple[str, ...]


@dataclass(frozen=True)
class RuleExceptionCodeTestCase:
    """Configured exception code and expected catalogue error."""

    description: str
    rule_code: str
    expected_error_fragment: str


@dataclass(frozen=True)
class CacheableRuleValidationTestCase:
    """One cacheable rule source and its expected catalogue validation outcome."""

    description: str
    prelude: str
    check_body: str
    expected_error_fragment: str | None
    expected_cacheable: bool | None


@dataclass(frozen=True)
class DeclaredCacheableRuleTestCase:
    """One decorator-declared cacheability outcome without the blanket policy."""

    description: str
    decorator_arguments: str
    prelude: str
    check_body: str
    expected_error_fragment: str | None
    expected_cacheable: bool | None


@dataclass(frozen=True)
class UndeclaredCacheableTestCase:
    """One custom rule source and its expected appears-cacheable report."""

    description: str
    decorator_arguments: str
    prelude: str
    expected_codes: tuple[str, ...]


@dataclass(frozen=True)
class ModuleUseTestCase:
    """One rule check shape and its expected raw-AST-use classification."""

    description: str
    check_name: str
    expected_uses_module: bool


@dataclass(frozen=True)
class CoreModuleFreedomTestCase:
    """One whole-catalogue raw-AST-freedom expectation."""

    description: str
    expected_minimum_rules: int
    expected_module_using_codes: tuple[str, ...]


@dataclass(frozen=True)
class LoadedModuleUseTestCase:
    """One loaded custom rule body and its expected raw-AST-use flag."""

    description: str
    rule_code: str
    check_body: str
    expected_uses_module: bool


@dataclass(frozen=True)
class UnselectedRuleOptionTestCase:
    """An unselected discovered rule and its expected option validation error."""

    description: str
    rule_code: str
    expected_error_fragment: str


@dataclass(frozen=True)
class NativeRulePackCatalogueTestCase:
    """Expected complete and active sizes for one shipped native rule pack."""

    description: str
    expected_catalogue_count: int
    expected_active_count: int
    expected_alias_count: int
    expected_native_count: int


@dataclass(frozen=True)
class NativeWebPackCatalogueTestCase:
    """Expected standalone TypeScript and SvelteKit pack composition."""

    description: str
    expected_typescript_count: int
    expected_sveltekit_count: int
    expected_alias_count: int
    expected_native_count: int


@dataclass(frozen=True)
class NativeRustPackCatalogueTestCase:
    """Expected standalone Rust structure pack composition."""

    description: str
    expected_rule_count: int


@dataclass(frozen=True)
class WebMigrationTestCase:
    """Expected complete web migration inventory facts."""

    description: str
    expected_rule_count: int
    expected_categories: frozenset[str]


@dataclass(frozen=True)
class WebPolicyProvenanceTestCase:
    """Expected configuration provenance for retained web policy."""

    description: str
    expected_ui_kit_rules: frozenset[str]
    expected_fwp_reason_fragment: str
