"""Public rule catalogue builder."""

from __future__ import annotations

from pathlib import Path

from strata.config.models import Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.helpers.loading import build_ruleset_from_config


def build_ruleset(*, config: Config, repo_root: Path | None = None) -> tuple[RuleSpec, ...]:
    """Build the selected ruleset from core and configured custom rules."""

    return build_ruleset_from_config(config=config, repo_root=repo_root)
