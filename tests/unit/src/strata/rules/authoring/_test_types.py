"""Test case types for rule authoring (decorator and class styles)."""

from __future__ import annotations

from dataclasses import dataclass

from strata.rules.spec.types import Family, RuleKind


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
