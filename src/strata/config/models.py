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
    """One centralized exact rule/path exception grouping qualified symbols."""

    rule: str
    path: str
    symbols: tuple[str, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class CacheConfig:
    """Operational persistent-cache preferences."""

    enabled: bool
    require_cacheable: bool = False


@dataclass(frozen=True, slots=True)
class Config:
    """Validated strata configuration."""

    roots: tuple[str, ...]
    tests: tuple[str, ...] = ("tests",)
    tooling: tuple[str, ...] = ()
    select: tuple[str, ...] = ("SF",)
    ignore: tuple[str, ...] = ()
    rule_paths: tuple[str, ...] = ()
    rule_modules: tuple[str, ...] = ()
    rule_exceptions: tuple[RuleExceptionEntry, ...] = ()
    cache: CacheConfig = field(default_factory=lambda: CacheConfig(enabled=DEFAULT_CACHE_ENABLED))
    thresholds: Mapping[Threshold, int] = field(
        default_factory=lambda: MappingProxyType(dict(DEFAULT_THRESHOLDS))
    )
    role_thresholds: Mapping[str, Mapping[Threshold, int]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    contracts: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType(dict(DEFAULT_CONTRACTS))
    )
