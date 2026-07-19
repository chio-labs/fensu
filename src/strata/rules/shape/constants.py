"""Shape rule constants."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.shape.main._shape_rules import shape_rules

SFS_RULES: tuple[RuleSpec, ...] = shape_rules()
