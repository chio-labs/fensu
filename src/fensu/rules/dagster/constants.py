"""Dagster native rule-pack catalogue constants."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.dagster.main._dagster_rules import dagster_rules

DAGSTER_PACK_NAME: str = "dagster"
FPDG_RULES: tuple[RuleSpec, ...] = dagster_rules()
FPDG_NATIVE_CODES: frozenset[str] = frozenset(
    rule.code for rule in FPDG_RULES if rule.alias_of is None
)
