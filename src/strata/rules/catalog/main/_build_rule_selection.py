"""Public resolved rule selection builder."""

from __future__ import annotations

from pathlib import Path

from strata.config.models import Config
from strata.rules.catalog._helpers.loading import build_rule_selection_from_config
from strata.rules.catalog.models import RuleSelection


def build_rule_selection(*, config: Config, repo_root: Path | None = None) -> RuleSelection:
    """Load one catalogue and resolve its configured policy tiers."""

    return build_rule_selection_from_config(config=config, repo_root=repo_root)
