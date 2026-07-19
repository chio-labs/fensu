"""Layer rule catalogue constants."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.layers.main._helper_rules import helper_rules
from fensu.rules.layers.main._import_rules import import_rules

FFL_RULES: tuple[RuleSpec, ...] = tuple(
    sorted((*import_rules(), *helper_rules()), key=lambda rule: rule.code)
)
