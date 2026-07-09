"""Public rule catalogue builder."""

from __future__ import annotations

from strata.config.core.models import Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.helpers.loading import build_ruleset_from_config


def build_ruleset(config: Config) -> tuple[RuleSpec, ...]:
    """Build the selected ruleset from core and configured custom rules."""

    return build_ruleset_from_config(config)
