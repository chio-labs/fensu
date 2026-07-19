"""Naming rule constants."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.naming.main._contract_rules import contract_rules

FFN_RULES: tuple[RuleSpec, ...] = contract_rules()
