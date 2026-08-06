"""Expose the native Dagster rule-pack catalogue."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.dagster._helpers.catalogue import build_dagster_rules


def dagster_rules() -> tuple[RuleSpec, ...]:
    """Return native Dagster rules and unchanged retained core aliases."""

    return build_dagster_rules()
