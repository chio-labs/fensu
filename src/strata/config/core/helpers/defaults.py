"""Merge validated user config with shipped defaults."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from strata.config.core.constants import (
    DEFAULT_CACHE_ENABLED,
    DEFAULT_CONTRACTS,
    DEFAULT_IGNORE,
    DEFAULT_SELECT,
    DEFAULT_TEST_PATHS,
    DEFAULT_THRESHOLDS,
    DEFAULT_TOOLING_PATHS,
)
from strata.config.core.models import CacheConfig, Config, RuleExceptionEntry
from strata.rules.authoring.types import Threshold


def build_config(raw: Mapping[str, object]) -> Config:
    """Build a Config by overlaying validated user values on shipped defaults."""

    thresholds: dict[Threshold, int] = dict(DEFAULT_THRESHOLDS)
    thresholds.update(_threshold_values(value=raw.get("thresholds")))
    role_thresholds: dict[str, Mapping[Threshold, int]] = {}
    roles: object = raw.get("roles")
    if isinstance(roles, dict):
        for role_name, role_values in roles.items():
            if isinstance(role_name, str):
                role_thresholds[role_name] = MappingProxyType(_threshold_values(value=role_values))
    contracts: dict[str, str] = dict(DEFAULT_CONTRACTS)
    raw_contracts: object = raw.get("contracts")
    if isinstance(raw_contracts, dict):
        contracts.update(
            {
                key: value
                for key, value in raw_contracts.items()
                if isinstance(key, str) and isinstance(value, str)
            }
        )
    return Config(
        roots=_string_tuple(value=raw["roots"]),
        tests=_string_tuple(value=raw.get("tests"), default=DEFAULT_TEST_PATHS),
        tooling=_string_tuple(value=raw.get("tooling"), default=DEFAULT_TOOLING_PATHS),
        select=_string_tuple(value=raw.get("select"), default=DEFAULT_SELECT),
        ignore=_string_tuple(value=raw.get("ignore"), default=DEFAULT_IGNORE),
        rule_paths=_string_tuple(value=raw.get("rule_paths")),
        rule_modules=_string_tuple(value=raw.get("rule_modules")),
        rule_exceptions=_rule_exceptions(raw.get("rule_exceptions")),
        cache=_cache_config(raw.get("cache")),
        thresholds=MappingProxyType(thresholds),
        role_thresholds=MappingProxyType(role_thresholds),
        contracts=MappingProxyType(contracts),
    )


def _cache_config(value: object) -> CacheConfig:
    if not isinstance(value, dict):
        return CacheConfig(enabled=DEFAULT_CACHE_ENABLED)
    enabled: object = value.get("enabled")
    return CacheConfig(
        enabled=enabled if isinstance(enabled, bool) else DEFAULT_CACHE_ENABLED,
    )


def _threshold_values(*, value: object) -> dict[Threshold, int]:
    if not isinstance(value, dict):
        return {}
    result: dict[Threshold, int] = {}
    for key, threshold_value in value.items():
        if isinstance(key, str) and isinstance(threshold_value, int):
            result[Threshold(key)] = threshold_value
    return result


def _string_tuple(*, value: object, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if value is None:
        return default
    if not isinstance(value, list):
        return default
    return tuple(item for item in value if isinstance(item, str))


def _rule_exceptions(value: object) -> tuple[RuleExceptionEntry, ...]:
    if not isinstance(value, list):
        return ()
    result: list[RuleExceptionEntry] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        rule: object = entry.get("rule")
        path: object = entry.get("path")
        symbols: object = entry.get("symbols")
        reason: object = entry.get("reason")
        if (
            isinstance(rule, str)
            and isinstance(path, str)
            and isinstance(symbols, list)
            and isinstance(reason, str)
        ):
            result.append(
                RuleExceptionEntry(
                    rule=rule,
                    path=path,
                    symbols=tuple(symbol for symbol in symbols if isinstance(symbol, str)),
                    reason=reason,
                )
            )
    return tuple(result)
