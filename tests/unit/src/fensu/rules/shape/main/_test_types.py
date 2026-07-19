"""Test case types for shape rules."""

from __future__ import annotations

from dataclasses import dataclass, field

from fensu.config.models import ThresholdOverride
from fensu.rules.authoring.types import Threshold


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


@dataclass(frozen=True)
class NativeThresholdOverrideUseTestCase:
    """Expected native threshold observations for one file position."""

    description: str
    relative_path: str
    expected_thresholds: tuple[Threshold, ...]
    expected_repository_path: str
    expected_effective_value: int
    expected_reason: str
