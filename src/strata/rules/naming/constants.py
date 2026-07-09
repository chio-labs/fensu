"""Naming rule constants."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.naming.main.contract_rules import contract_rules

SFN_RULES: tuple[RuleSpec, ...] = contract_rules()
