"""Test case types for repository-aware skill guidance."""

from __future__ import annotations

from dataclasses import dataclass

from strata.config.core.models import Config


@dataclass(frozen=True)
class GuidanceTestCase:
    """Config, active rules, and expected generated guidance."""

    description: str
    config: Config
    rule_codes: tuple[str, ...]
    expected_fragments: tuple[str, ...]
    expected_absent_fragments: tuple[str, ...]
