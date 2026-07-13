"""Configuration models produced by the config loading pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from strata.config.constants import (
    DEFAULT_CACHE_ENABLED,
    DEFAULT_CONTRACTS,
    DEFAULT_THRESHOLDS,
)
from strata.config.types import ConfigSourceKind
from strata.rules.authoring.types import Threshold


@dataclass(frozen=True, slots=True)
class ConfigSource:
    """The config source selected by discovery."""

    path: Path
    kind: ConfigSourceKind


@dataclass(frozen=True, slots=True)
class LoadedConfig:
    """Validated configuration paired with its selected source."""

    config: Config
    source: ConfigSource


@dataclass(frozen=True, slots=True)
class RuleExceptionEntry:
    """One centralized exact rule/path exception with optional qualified symbols."""

    rule: str
    path: str
    reason: str
    symbols: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CacheConfig:
    """Operational persistent-cache preferences."""

    enabled: bool
    require_cacheable: bool = False


@dataclass(frozen=True, slots=True)
class EvaluationConfig:
    """Repository-relative paths eligible for direct rule evaluation."""

    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SkillsConfig:
    """Persistent generated-skill identity preferences."""

    name: str | None = None


@dataclass(frozen=True, slots=True)
class ThresholdOverride:
    """Path-scoped threshold values with an explicit justification."""

    paths: tuple[str, ...]
    thresholds: Mapping[Threshold, int]
    reason: str

    def __post_init__(self) -> None:
        """Freeze a defensive copy of threshold values supplied by public callers."""

        object.__setattr__(self, "thresholds", MappingProxyType(dict(self.thresholds)))


@dataclass(frozen=True, slots=True)
class ThresholdResolution:
    """One effective threshold resolution for a repository-relative reported path."""

    threshold: Threshold
    effective_value: int
    repository_path: str
    matched_pattern: str | None = None
    reason: str | None = None
    override_order: int | None = None


@dataclass(frozen=True, slots=True)
class Config:
    """Validated strata configuration."""

    roots: tuple[str, ...]
    tests: tuple[str, ...] = ("tests",)
    tooling: tuple[str, ...] = ()
    select: tuple[str, ...] = ("SF",)
    warn: tuple[str, ...] = ()
    ignore: tuple[str, ...] = ()
    rule_paths: tuple[str, ...] = ()
    rule_modules: tuple[str, ...] = ()
    rule_exceptions: tuple[RuleExceptionEntry, ...] = ()
    cache: CacheConfig = field(default_factory=lambda: CacheConfig(enabled=DEFAULT_CACHE_ENABLED))
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    thresholds: Mapping[Threshold, int] = field(
        default_factory=lambda: MappingProxyType(dict(DEFAULT_THRESHOLDS))
    )
    role_thresholds: Mapping[str, Mapping[Threshold, int]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    threshold_overrides: tuple[ThresholdOverride, ...] = ()
    contracts: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType(dict(DEFAULT_CONTRACTS))
    )
