"""Test cases for native Dagster rule behavior."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from fensu import RuleFile
from fensu.rules.authoring.types import RuleOptionValue


@dataclass(frozen=True)
class NativeDagsterRuleTestCase:
    """One native Dagster rule example and its expected diagnostic count."""

    description: str
    code: str
    source: str
    path: str
    expected_fault_count: int
    files: tuple[RuleFile, ...] = ()
    rule_options: Mapping[str, RuleOptionValue] | None = None
    scope: str = "root"
