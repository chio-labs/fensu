"""Shape rule constants."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.shape.main._shape_rules import shape_rules

FFS_RULES: tuple[RuleSpec, ...] = shape_rules()
