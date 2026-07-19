"""Test case types for repository-aware skill guidance."""

from __future__ import annotations

from dataclasses import dataclass

from strata.agentdocs.models import SkillGenerationContext
from strata.config.models import Config


@dataclass(frozen=True)
class GuidanceTestCase:
    """Config, active rules, and expected generated guidance."""

    description: str
    config: Config
    rule_codes: tuple[str, ...]
    expected_fragments: tuple[str, ...]
    expected_absent_fragments: tuple[str, ...]


@dataclass(frozen=True)
class SkillContentTestCase:
    """Generation context and mandatory product content assertions."""

    description: str
    context: SkillGenerationContext
    expected_fragments: tuple[str, ...]
    expected_absent_fragments: tuple[str, ...]


@dataclass(frozen=True)
class SkillDeterminismTestCase:
    """Equivalent generation contexts and expected byte equality."""

    description: str
    first_context: SkillGenerationContext
    second_context: SkillGenerationContext
    expected_equal: bool


@dataclass(frozen=True)
class SkillContextImmutabilityTestCase:
    """Generation context and expected mutation failure."""

    description: str
    context: SkillGenerationContext
    expected_error_type: type[Exception]
