"""Hygiene rule constants."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.hygiene.main._hygiene_rules import hygiene_rules

SFH_RULES: tuple[RuleSpec, ...] = hygiene_rules()
