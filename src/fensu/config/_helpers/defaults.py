"""Merge validated user config with shipped defaults."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from fensu.config.constants import (
    CACHE_ENABLED_CONFIG_KEY,
    CACHE_REQUIRE_CACHEABLE_CONFIG_KEY,
    DEFAULT_CACHE_ENABLED,
    DEFAULT_CACHE_REQUIRE_CACHEABLE,
    DEFAULT_CONTRACTS,
    DEFAULT_EXPERIMENTAL_MEMORY,
    DEFAULT_IGNORE,
    DEFAULT_MEMORY_TASKS_ARCHIVE_AFTER_DAYS,
    DEFAULT_SELECT,
    DEFAULT_TEST_PATHS,
    DEFAULT_THRESHOLDS,
    DEFAULT_TOOLING_PATHS,
    DEFAULT_WARN,
    EXPERIMENTAL_MEMORY_CONFIG_KEY,
    MEMORY_TASKS_ARCHIVE_AFTER_DAYS_CONFIG_KEY,
    MEMORY_TASKS_CONFIG_KEY,
    SKILLS_NAME_CONFIG_KEY,
)
from fensu.config.models import (
    CacheConfig,
    Config,
    EvaluationConfig,
    ExperimentalConfig,
    MemoryConfig,
    MemoryTasksConfig,
    RuleExceptionEntry,
    RuleIgnoreEntry,
    SkillsConfig,
    ThresholdOverride,
)
from fensu.rules.authoring.types import RuleOptionValue, Threshold


def build_config(
    *,
    raw: Mapping[str, object],
    rule_options: Mapping[str, Mapping[str, RuleOptionValue]] | None = None,
) -> Config:
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
        warn=_string_tuple(value=raw.get("warn"), default=DEFAULT_WARN),
        ignore=_string_tuple(value=raw.get("ignore"), default=DEFAULT_IGNORE),
        rule_paths=_string_tuple(value=raw.get("rule_paths")),
        rule_modules=_string_tuple(value=raw.get("rule_modules")),
        rule_options=MappingProxyType({}) if rule_options is None else rule_options,
        rule_exceptions=_rule_exceptions(raw.get("rule_exceptions")),
        rule_ignores=_rule_ignores(raw.get("rule_ignores")),
        cache=_cache_config(raw.get("cache")),
        experimental=_experimental_config(raw.get("experimental")),
        memory=_memory_config(raw.get("memory")),
        evaluation=_evaluation_config(raw.get("evaluation")),
        skills=_skills_config(raw.get("skills")),
        thresholds=MappingProxyType(thresholds),
        role_thresholds=MappingProxyType(role_thresholds),
        threshold_overrides=_threshold_overrides(raw.get("threshold_overrides")),
        contracts=MappingProxyType(contracts),
    )


def _skills_config(value: object) -> SkillsConfig:
    if not isinstance(value, dict):
        return SkillsConfig()
    name: object = value.get(SKILLS_NAME_CONFIG_KEY)
    return SkillsConfig(name=name if isinstance(name, str) else None)


def _evaluation_config(value: object) -> EvaluationConfig:
    if not isinstance(value, dict):
        return EvaluationConfig()
    return EvaluationConfig(
        include=_string_tuple(value=value.get("include")),
        exclude=_string_tuple(value=value.get("exclude")),
    )


def _memory_config(value: object) -> MemoryConfig:
    if not isinstance(value, dict):
        return MemoryConfig()
    return MemoryConfig(
        tasks=_memory_tasks_config(value.get(MEMORY_TASKS_CONFIG_KEY)),
    )


def _experimental_config(value: object) -> ExperimentalConfig:
    if not isinstance(value, dict):
        return ExperimentalConfig()
    memory: object = value.get(EXPERIMENTAL_MEMORY_CONFIG_KEY)
    return ExperimentalConfig(
        memory=memory if isinstance(memory, bool) else DEFAULT_EXPERIMENTAL_MEMORY
    )


def _memory_tasks_config(value: object) -> MemoryTasksConfig:
    if not isinstance(value, dict):
        return MemoryTasksConfig()
    archive_after_days: object = value.get(MEMORY_TASKS_ARCHIVE_AFTER_DAYS_CONFIG_KEY)
    return MemoryTasksConfig(
        archive_after_days=(
            archive_after_days
            if type(archive_after_days) is int
            else DEFAULT_MEMORY_TASKS_ARCHIVE_AFTER_DAYS
        )
    )


def _cache_config(value: object) -> CacheConfig:
    if not isinstance(value, dict):
        return CacheConfig(enabled=DEFAULT_CACHE_ENABLED)
    enabled: object = value.get(CACHE_ENABLED_CONFIG_KEY)
    require_cacheable: object = value.get(CACHE_REQUIRE_CACHEABLE_CONFIG_KEY)
    return CacheConfig(
        enabled=enabled if isinstance(enabled, bool) else DEFAULT_CACHE_ENABLED,
        require_cacheable=(
            require_cacheable
            if isinstance(require_cacheable, bool)
            else DEFAULT_CACHE_REQUIRE_CACHEABLE
        ),
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
        symbols: object = entry.get("symbols", [])
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
                    reason=reason,
                    symbols=tuple(symbol for symbol in symbols if isinstance(symbol, str)),
                )
            )
    return tuple(result)


def _rule_ignores(value: object) -> tuple[RuleIgnoreEntry, ...]:
    if not isinstance(value, list):
        return ()
    result: list[RuleIgnoreEntry] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        rules: object = entry.get("rules")
        paths: object = entry.get("paths")
        reason: object = entry.get("reason")
        if isinstance(rules, list) and isinstance(paths, list) and isinstance(reason, str):
            result.append(
                RuleIgnoreEntry(
                    rules=tuple(rule for rule in rules if isinstance(rule, str)),
                    paths=tuple(path for path in paths if isinstance(path, str)),
                    reason=reason,
                )
            )
    return tuple(result)


def _threshold_overrides(value: object) -> tuple[ThresholdOverride, ...]:
    if not isinstance(value, list):
        return ()
    result: list[ThresholdOverride] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        paths: object = entry.get("paths")
        reason: object = entry.get("reason")
        thresholds: object = entry.get("thresholds")
        if isinstance(paths, list) and isinstance(reason, str):
            result.append(
                ThresholdOverride(
                    paths=tuple(path for path in paths if isinstance(path, str)),
                    thresholds=MappingProxyType(_threshold_values(value=thresholds)),
                    reason=reason,
                )
            )
    return tuple(result)
