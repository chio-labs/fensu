"""Rule catalogue constants."""

from __future__ import annotations

from strata.rules.annotations.constants import SFA_RULES
from strata.rules.authoring.models import RuleSpec
from strata.rules.hygiene.constants import SFX_RULES
from strata.rules.layers.constants import SFL_RULES
from strata.rules.roles.constants import SFR_RULES
from strata.rules.shape.constants import SFS_RULES
from strata.rules.tests.constants import SFT_RULES

CORE_RULES: tuple[RuleSpec, ...] = (
    *SFA_RULES,
    *SFL_RULES,
    *SFX_RULES,
    *SFS_RULES,
    *SFT_RULES,
    *SFR_RULES,
)
