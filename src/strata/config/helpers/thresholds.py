"""Resolve global, role, and path-scoped thresholds."""

from __future__ import annotations

from collections.abc import Mapping

from strata.config.helpers.path_patterns import path_pattern_matches, path_pattern_specificity
from strata.config.models import Config, ThresholdOverride, ThresholdResolution
from strata.rules.authoring.types import Threshold


def resolve_threshold(
    *, config: Config, name: Threshold, path: str, role: str | None
) -> ThresholdResolution:
    """Return the effective value and winning path override details."""

    winner: tuple[tuple[int, int, int, int], int, ThresholdOverride, str] | None = None
    for declaration_order, override in enumerate(config.threshold_overrides):
        if name not in override.thresholds:
            continue
        for pattern in override.paths:
            if not path_pattern_matches(pattern=pattern, path=path):
                continue
            candidate: tuple[tuple[int, int, int, int], int, ThresholdOverride, str] = (
                path_pattern_specificity(pattern),
                declaration_order,
                override,
                pattern,
            )
            if winner is None or candidate[:2] >= winner[:2]:
                winner = candidate
    if winner is not None:
        return ThresholdResolution(
            threshold=name,
            effective_value=winner[2].thresholds[name],
            repository_path=path,
            matched_pattern=winner[3],
            reason=winner[2].reason,
            override_order=winner[1],
        )
    if role is not None:
        role_thresholds: Mapping[Threshold, int] | None = config.role_thresholds.get(role)
        if role_thresholds is not None and name in role_thresholds:
            return ThresholdResolution(
                threshold=name, effective_value=role_thresholds[name], repository_path=path
            )
    return ThresholdResolution(
        threshold=name, effective_value=config.thresholds[name], repository_path=path
    )
