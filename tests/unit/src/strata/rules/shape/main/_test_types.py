"""Test case types for shape rules."""

from __future__ import annotations

from dataclasses import dataclass, field

from strata.config.models import ThresholdOverride
from strata.rules.authoring.types import Threshold


@dataclass(frozen=True)
class ShapeRuleTestCase:
    """Shape rule source and expected fault facts."""

    description: str
    rule_code: str
    source: str
    expected_codes: tuple[str, ...]
    expected_lines: tuple[int | None, ...]
    relative_path: str = "domain/core/main/run.py"
    project_files: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    thresholds: dict[Threshold, int] = field(default_factory=dict)
    role_thresholds: dict[str, dict[Threshold, int]] = field(default_factory=dict)
    threshold_overrides: tuple[ThresholdOverride, ...] = ()
    root: str = "src/pkg"
