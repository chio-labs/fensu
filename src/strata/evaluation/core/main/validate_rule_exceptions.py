"""Validate centralized rule-exception repository targets."""

from __future__ import annotations

from pathlib import Path

from strata.config.core.models import Config
from strata.evaluation.core.helpers.rule_exceptions import validate_exception_targets


def validate_rule_exceptions(*, config: Config, repo_root: Path) -> None:
    """Validate exact configured exception paths and symbols before evaluation."""

    validate_exception_targets(config=config, repo_root=repo_root)
