"""Rule catalogue constants."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.layers.constants import SFL_RULES

CORE_RULES: tuple[RuleSpec, ...] = (*SFL_RULES,)
