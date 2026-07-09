"""Layer rule catalogue constants."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.layers.main.helper_rules import helper_rules
from strata.rules.layers.main.import_rules import import_rules

SFL_RULES: tuple[RuleSpec, ...] = tuple(
    sorted((*import_rules(), *helper_rules()), key=lambda rule: rule.code)
)
