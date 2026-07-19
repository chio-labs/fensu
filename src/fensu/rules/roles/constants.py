"""Roles rule constants."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.roles.main._content_rules import content_rules
from fensu.rules.roles.main._layout_rules import layout_rules
from fensu.rules.roles.main._misplaced_rules import misplaced_rules
from fensu.rules.roles.main._naming_rules import naming_rules
from fensu.rules.roles.main._shape_rules import shape_rules
from fensu.rules.roles.main._surface_rules import surface_rules
from fensu.rules.roles.main._tooling_rules import tooling_rules

FFR_RULES: tuple[RuleSpec, ...] = (
    *content_rules(),
    *misplaced_rules(),
    *naming_rules(),
    *layout_rules(),
    *surface_rules(),
    *shape_rules(),
    *tooling_rules(),
)
