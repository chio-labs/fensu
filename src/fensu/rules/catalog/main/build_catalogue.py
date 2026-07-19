"""Public complete rule catalogue builder."""

from __future__ import annotations

from pathlib import Path

from fensu.config.models import Config
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.catalog._helpers.loading import build_catalogue_from_config


def build_catalogue(*, config: Config, repo_root: Path | None = None) -> tuple[RuleSpec, ...]:
    """Build all core and configured custom rules without selection filtering."""

    return build_catalogue_from_config(config=config, repo_root=repo_root)
