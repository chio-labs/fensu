"""Hygiene rule constants."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.hygiene.main.hygiene_rules import hygiene_rules

SFX_RULES: tuple[RuleSpec, ...] = hygiene_rules()
