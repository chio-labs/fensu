"""Test case types for roles rules."""

from __future__ import annotations

from dataclasses import dataclass, field

from strata.config.models import ThresholdOverride
from strata.discovery.types import ScopeName
from strata.rules.authoring.types import Threshold


@dataclass(frozen=True)
class SfrSupportFile:
    """An additional file used to construct a role layout."""

    description: str
    relative_path: str
    source: str
    expected_written: bool = True
    is_directory: bool = False


@dataclass(frozen=True)
class SfrRuleTestCase:
    """Roles rule source and expected fault facts."""

    description: str
    rule_code: str
    relative_path: str
    source: str
    expected_codes: tuple[str, ...]
    expected_lines: tuple[int | None, ...]
    support_files: tuple[SfrSupportFile, ...] = field(default_factory=tuple)
    thresholds: dict[Threshold, int] = field(default_factory=dict)
    threshold_overrides: tuple[ThresholdOverride, ...] = field(default_factory=tuple)
    expected_messages: tuple[str, ...] = field(default_factory=tuple)
    expected_remediations: tuple[str, ...] = field(default_factory=tuple)
    expected_paths: tuple[str, ...] = field(default_factory=tuple)
    scope: ScopeName = ScopeName.ROOT


@dataclass(frozen=True)
class ContainerScaleTestCase:
    """Two role widths and expected near-linear project-query growth."""

    description: str
    small_module_count: int
    large_module_count: int
    expected_max_query_multiplier: int
    expected_small_fault_count: int
    expected_large_fault_count: int
