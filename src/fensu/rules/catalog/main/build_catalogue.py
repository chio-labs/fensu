"""Build the complete core and custom rule catalogue for one repository."""

from __future__ import annotations

from pathlib import Path

from fensu.config.models import Config
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.catalog._helpers.loading import build_catalogue_from_config


def build_catalogue(*, config: Config, repo_root: Path) -> tuple[RuleSpec, ...]:
    """Return all deterministically discovered core and custom rules."""

    return build_catalogue_from_config(config=config, repo_root=repo_root)
