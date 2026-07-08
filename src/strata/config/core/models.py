"""Configuration models produced by the config loading pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from strata.config.core.constants import DEFAULT_CONTRACTS, DEFAULT_THRESHOLDS
from strata.rules.authoring.types import Threshold


@dataclass(frozen=True, slots=True)
class ConfigSource:
    """The config source selected by discovery."""

    path: Path
    kind: Literal["strata_toml", "pyproject"]


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
    thresholds: Mapping[Threshold, int] = field(
        default_factory=lambda: MappingProxyType(dict(DEFAULT_THRESHOLDS))
    )
    role_thresholds: Mapping[str, Mapping[Threshold, int]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    contracts: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType(dict(DEFAULT_CONTRACTS))
    )
