"""Resolve one effective threshold at a repository-relative reported path."""

from __future__ import annotations

from strata.config.helpers.thresholds import resolve_threshold as resolve_threshold_value
from strata.config.models import Config, ThresholdResolution
from strata.rules.authoring.types import Threshold


def resolve_threshold(
    *, config: Config, name: Threshold, path: str, role: str | None
) -> ThresholdResolution:
    """Return the effective value and winning path override details."""

    return resolve_threshold_value(config=config, name=name, path=path, role=role)
