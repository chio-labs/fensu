"""Validate raw config mappings and raise clear schema errors."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import PurePosixPath

from strata.config.core.constants import (
    CONFIG_ROLE_NAMES,
    CONFIG_TOP_LEVEL_KEYS,
    CONTRACT_BEHAVIORS,
)
from strata.config.core.exceptions import ConfigError, ConfigValidationError
from strata.config.core.types import RuleSelector
from strata.rules.authoring.types import Threshold


def validate_config(raw: Mapping[str, object]) -> None:
    """Raise if a raw config mapping violates the day-one schema."""

    _validate_top_level_keys(raw=raw)
    roots: tuple[str, ...] = _validate_string_sequence(name="roots", value=raw.get("roots"))
    if len(roots) == 0:
        raise ConfigError("Config must define at least one root in roots.")
    _validate_no_nested_paths(name="roots", paths=roots)
    _validate_optional_string_sequence(name="tests", value=raw.get("tests"))
    _validate_optional_string_sequence(name="tooling", value=raw.get("tooling"))
    _validate_optional_string_sequence(name="rule_paths", value=raw.get("rule_paths"))
    _validate_optional_string_sequence(name="rule_modules", value=raw.get("rule_modules"))
    _validate_selection(name="select", value=raw.get("select"))
    _validate_selection(name="ignore", value=raw.get("ignore"))
    _validate_thresholds(value=raw.get("thresholds"), owner="thresholds")
    _validate_role_thresholds(value=raw.get("roles"))
    _validate_contracts(value=raw.get("contracts"))


def _validate_top_level_keys(*, raw: Mapping[str, object]) -> None:
    unknown_keys: set[str] = set(raw) - set(CONFIG_TOP_LEVEL_KEYS)
    if unknown_keys:
        names: str = ", ".join(sorted(unknown_keys))
        raise ConfigValidationError(f"Unknown config key(s): {names}.")


def _validate_string_sequence(*, name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ConfigError(f"Config key {name} must be a list of strings.")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ConfigValidationError(f"Config key {name} must contain non-empty strings.")
        result.append(item)
    return tuple(result)


def _validate_optional_string_sequence(*, name: str, value: object) -> None:
    if value is None:
        return
    _ = _validate_string_sequence(name=name, value=value)


def _validate_no_nested_paths(*, name: str, paths: tuple[str, ...]) -> None:
    normalized_paths: tuple[tuple[str, ...], ...] = tuple(
        PurePosixPath(path).parts for path in paths
    )
    for index, parent in enumerate(normalized_paths):
        for child in normalized_paths[index + 1 :]:
            if _path_parts_nested(first=parent, second=child):
                raise ConfigError(f"Config key {name} must not contain nested paths.")


def _path_parts_nested(*, first: tuple[str, ...], second: tuple[str, ...]) -> bool:
    shortest_length: int = min(len(first), len(second))
    return first[:shortest_length] == second[:shortest_length]


def _validate_selection(*, name: str, value: object) -> None:
    if value is None:
        return
    entries: tuple[str, ...] = _validate_string_sequence(name=name, value=value)
    for entry in entries:
        if not _selection_entry_is_well_formed(entry):
            raise ConfigValidationError(f"Config key {name} contains invalid selector {entry}.")


def _selection_entry_is_well_formed(entry: str) -> bool:
    if entry == RuleSelector.ALL:
        return True
    family_selectors: set[str] = {
        selector for selector in RuleSelector if selector is not RuleSelector.ALL
    }
    if entry in family_selectors:
        return True
    family_letters: str = "".join(selector[-1] for selector in sorted(family_selectors))
    return (
        re.fullmatch(rf"SF[{family_letters}][0-9]{{3}}", entry) is not None
        or re.fullmatch(r"X[A-Za-z0-9][A-Za-z0-9_-]*", entry) is not None
    )


def _validate_thresholds(*, value: object, owner: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ConfigValidationError(f"Config key {owner} must be a table of integer thresholds.")
    valid_thresholds: set[str] = {threshold.value for threshold in Threshold}
    for key, threshold_value in value.items():
        if not isinstance(key, str) or key not in valid_thresholds:
            raise ConfigValidationError(f"Unknown threshold key in {owner}: {key}.")
        if not isinstance(threshold_value, int):
            raise ConfigValidationError(f"Threshold {key} in {owner} must be an integer.")
        if threshold_value < 0:
            raise ConfigValidationError(f"Threshold {key} in {owner} must be non-negative.")


def _validate_role_thresholds(*, value: object) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ConfigValidationError("Config key roles must be a table of role threshold tables.")
    for role_name, thresholds in value.items():
        if not isinstance(role_name, str) or role_name not in CONFIG_ROLE_NAMES:
            raise ConfigValidationError(f"Unknown role name in roles: {role_name}.")
        _validate_thresholds(value=thresholds, owner=f"roles.{role_name}")


def _validate_contracts(*, value: object) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ConfigValidationError("Config key contracts must be a table.")
    for pattern, behavior in value.items():
        if not isinstance(pattern, str) or not pattern:
            raise ConfigValidationError("Config contract patterns must be non-empty strings.")
        if behavior not in CONTRACT_BEHAVIORS:
            raise ConfigValidationError(f"Unknown contract behavior for {pattern}: {behavior}.")
