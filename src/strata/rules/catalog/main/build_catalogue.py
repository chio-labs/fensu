"""Public complete rule catalogue builder."""

from __future__ import annotations

from strata.config.core.models import Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.helpers.loading import build_catalogue_from_config


def build_catalogue(config: Config) -> tuple[RuleSpec, ...]:
    """Build all core and configured custom rules without selection filtering."""

    return build_catalogue_from_config(config)
