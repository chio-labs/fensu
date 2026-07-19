"""Hygiene rule constants."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.hygiene.main._hygiene_rules import hygiene_rules

FFH_RULES: tuple[RuleSpec, ...] = hygiene_rules()
