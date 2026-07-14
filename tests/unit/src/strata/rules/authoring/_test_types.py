"""Test case types for rule authoring (decorator and class styles)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from strata.rules.authoring.types import Family, RuleKind


@dataclass(frozen=True)
class FaultFormatTestCase:
    """A Fault rendered against a repo root into a text line."""

    description: str
    code: str
    path: Path
    message: str
    line: int | None
    column: int | None
    root: Path
    expected_rendered: str


@dataclass(frozen=True)
class EnumMembersTestCase:
    """An enum's actual and expected member-name-to-value mapping."""

    description: str
    actual_members: dict[str, str]
    expected_members: dict[str, str]


@dataclass(frozen=True)
class RuleEnvelopeTestCase:
    """A set of envelope arguments and the rule identity they should produce."""

    description: str
    code: str
    family: Family | str
    slug: str
    message: str
    expected_code: str
    expected_family: Family
    expected_kind: RuleKind


@dataclass(frozen=True)
class InvalidEnvelopeTestCase:
    """A set of envelope arguments that should be rejected at definition time."""

    description: str
    code: str
    family: Family | str
    slug: str
    message: str
    expected_error_fragment: str


@dataclass(frozen=True)
class ModuleMetadataTestCase:
    """A module metadata discovery scenario and expected rule codes."""

    description: str
    expected_codes: tuple[str, ...]


@dataclass(frozen=True)
class DirectModuleRuleCodeTestCase:
    """Direct module specs and their expected inspection result."""

    description: str
    code: object
    definition_count: int
    expected_rule_count: int


@dataclass(frozen=True)
class HermeticityTestCase:
    """One rule-execution hermeticity scan and its expected clean outcome."""

    description: str
    excluded_packages: tuple[str, ...]
    expected_minimum_modules: int
    expected_violations: tuple[str, ...]


@dataclass(frozen=True)
class RuleGrammarTestCase:
    """One spelling and its expected exact-code and selector classifications."""

    description: str
    value: object
    expected_is_code: bool
    expected_is_selector: bool


@dataclass(frozen=True)
class RuleSelectorMatchTestCase:
    """One code and selector pair with its expected spelling-only match."""

    description: str
    code: str
    selector: str
    expected_matches: bool


@dataclass(frozen=True)
class RuleCacheableFlagTestCase:
    """One decorator cacheability declaration and its recorded spec value."""

    description: str
    cacheable: bool | None
    expected_cacheable: bool | None
