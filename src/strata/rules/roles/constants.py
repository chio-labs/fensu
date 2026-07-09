"""Roles rule constants."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.roles.main.content_rules import content_rules
from strata.rules.roles.main.layout_rules import layout_rules
from strata.rules.roles.main.misplaced_rules import misplaced_rules
from strata.rules.roles.main.naming_rules import naming_rules

SFR_RULES: tuple[RuleSpec, ...] = (
    *content_rules(),
    *misplaced_rules(),
    *naming_rules(),
    *layout_rules(),
)
