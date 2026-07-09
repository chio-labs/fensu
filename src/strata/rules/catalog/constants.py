"""Rule catalogue constants."""

from __future__ import annotations

from strata.rules.annotations.constants import SFA_RULES
from strata.rules.authoring.models import RuleSpec
from strata.rules.layers.constants import SFL_RULES

CORE_RULES: tuple[RuleSpec, ...] = (*SFA_RULES, *SFL_RULES)
