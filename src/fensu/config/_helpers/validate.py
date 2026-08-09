"""Validate raw config mappings and raise clear schema errors."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import PurePosixPath, PureWindowsPath
from typing import cast

from fensu.config.constants import (
    CACHE_ENABLED_CONFIG_KEY,
    CACHE_REQUIRE_CACHEABLE_CONFIG_KEY,
    CONFIG_ROLE_NAMES,
    CONFIG_TOP_LEVEL_KEYS,
    CONTRACT_BEHAVIORS,
    DEFAULT_TARGET_ROOT,
    DOUBLE_PATH_SEPARATOR,
    EVALUATION_CONFIG_KEYS,
    MAX_THRESHOLD_VALUE,
    PATH_SEPARATOR,
    PYTHON_ANALYZER,
    RECURSIVE_GLOB,
    RULE_EXCEPTION_SYMBOLS_CONFIG_KEY,
    RULE_IGNORE_KEYS,
    SKILLS_CONFIG_KEYS,
    SKILLS_NAME_CONFIG_KEY,
    TARGET_CONFIG_KEYS,
    TARGETS_CONFIG_KEY,
    TEST_SCOPE_PATTERN,
    THRESHOLD_OVERRIDE_KEYS,
)
from fensu.config.exceptions import ConfigError, ConfigValidationError
from fensu.config.types import AnalyzerId
from fensu.rules.authoring.main.is_rule_code import is_rule_code
from fensu.rules.authoring.main.is_rule_selector import is_rule_selector
from fensu.rules.authoring.types import Threshold

_empty_string: str = ""
_windows_path_separator: str = "\\"
_current_path_part: str = "."
_parent_path_part: str = ".."
_python_file_suffix: str = ".py"
_glob_characters: frozenset[str] = frozenset({"*", "?", "[", "]"})
_registered_rule_packs: frozenset[str] = frozenset({"dagster"})


def validate_config(raw: Mapping[str, object]) -> None:
    """Raise if a raw config mapping violates the day-one schema."""

    _validate_top_level_keys(raw=raw)
    roots: tuple[str, ...] = _validate_string_sequence(name="roots", value=raw.get("roots"))
    if len(roots) == 0:
        raise ConfigError("Config must define at least one root in roots.")
    _validate_no_nested_paths(name="roots", paths=roots)
    _validate_optional_string_sequence(name="tests", value=raw.get("tests"))
    _validate_test_scopes(value=raw.get("test_scopes"))
    _validate_optional_string_sequence(name="tooling", value=raw.get("tooling"))
    _validate_optional_string_sequence(name="rule_paths", value=raw.get("rule_paths"))
    _validate_optional_string_sequence(name="rule_modules", value=raw.get("rule_modules"))
    raw_rule_packs: object = raw.get("rule_packs")
    rule_packs: tuple[str, ...] = (
        ()
        if raw_rule_packs is None
        else _validate_string_sequence(name="rule_packs", value=raw_rule_packs)
    )
    if len(rule_packs) != len(set(rule_packs)):
        raise ConfigValidationError("Config key rule_packs must not contain duplicates.")
    unknown_rule_packs: tuple[str, ...] = tuple(sorted(set(rule_packs) - _registered_rule_packs))
    if unknown_rule_packs:
        raise ConfigValidationError(f"Unknown native rule pack: {unknown_rule_packs[0]}.")
    _validate_rule_options_shape(value=raw.get("rule_options"))
    _validate_selection(name="select", value=raw.get("select"))
    _validate_selection(name="warn", value=raw.get("warn"))
    _validate_selection(name="ignore", value=raw.get("ignore"))
    _validate_thresholds(value=raw.get("thresholds"), owner="thresholds")
    _validate_role_thresholds(value=raw.get("roles"))
    _validate_threshold_overrides(value=raw.get("threshold_overrides"))
    _validate_contracts(value=raw.get("contracts"))
    _validate_rule_exceptions(value=raw.get("rule_exceptions"))
    _validate_rule_ignores(value=raw.get("rule_ignores"))
    _validate_cache(value=raw.get("cache"))
    _validate_evaluation(value=raw.get("evaluation"))
    _validate_skills(value=raw.get("skills"))


def select_config_target(
    *, raw: Mapping[str, object], target: str | None
) -> tuple[Mapping[str, object], str | None, AnalyzerId, str]:
    """Select and validate one explicit target, or preserve legacy flat configuration."""

    if TARGETS_CONFIG_KEY not in raw:
        if target is not None:
            raise ConfigValidationError(f"Unknown target name: {target}.")
        return raw, None, PYTHON_ANALYZER, DEFAULT_TARGET_ROOT
    mixed_keys: set[str] = set(raw) - {TARGETS_CONFIG_KEY}
    if mixed_keys:
        names: str = ", ".join(sorted(mixed_keys))
        raise ConfigValidationError(
            f"Explicit targets cannot be mixed with legacy top-level config keys: {names}."
        )
    targets: object = raw.get(TARGETS_CONFIG_KEY)
    if not isinstance(targets, dict):
        raise ConfigValidationError("Config key targets must be a table of named targets.")
    if not targets:
        raise ConfigValidationError("Config key targets must define at least one named target.")
    validated: dict[str, tuple[dict[str, object], AnalyzerId, str]] = {}
    for name, value in sorted(targets.items()):
        if not isinstance(name, str) or not name:
            raise ConfigValidationError("Target names must be non-empty strings.")
        if not isinstance(value, dict):
            raise ConfigValidationError(f"Config target {name} must be a table.")
        typed_value: dict[str, object] = cast("dict[str, object]", value)
        unknown_keys: set[str] = (
            set(typed_value) - set(CONFIG_TOP_LEVEL_KEYS) - set(TARGET_CONFIG_KEYS)
        )
        if unknown_keys:
            names = ", ".join(sorted(unknown_keys))
            raise ConfigValidationError(f"Unknown targets.{name} config key(s): {names}.")
        analyzer: object = typed_value.get("analyzer")
        if not isinstance(analyzer, str) or not analyzer:
            raise ConfigValidationError(
                f"Config key targets.{name}.analyzer must be a non-empty string."
            )
        try:
            analyzer_id: AnalyzerId = AnalyzerId(analyzer)
        except ValueError:
            raise ConfigValidationError(
                f"Unknown analyzer for target {name}: {analyzer}."
            ) from None
        root_value: object = typed_value.get("root", DEFAULT_TARGET_ROOT)
        if not isinstance(root_value, str) or not root_value:
            raise ConfigValidationError(
                f"Config key targets.{name}.root must be a non-empty string."
            )
        root: str = _normalize_target_root(name=name, value=root_value)
        selected: dict[str, object] = dict(typed_value)
        _ = selected.pop("analyzer")
        _ = selected.pop("root", None)
        validate_config(selected)
        validated[name] = (selected, analyzer_id, root)
    selected_name: str
    if target is not None:
        if target not in validated:
            raise ConfigValidationError(f"Unknown target name: {target}.")
        selected_name = target
    elif len(validated) == 1:
        selected_name = next(iter(validated))
    else:
        raise ConfigValidationError(
            "Multiple targets are configured; select one with --target TARGET."
        )
    selected_config, analyzer, root = validated[selected_name]
    return selected_config, selected_name, analyzer, root


def selected_config_target_names(
    *, raw: Mapping[str, object], target: str | None
) -> tuple[str | None, ...]:
    """Return validated selected target names in deterministic order."""

    if target is not None or TARGETS_CONFIG_KEY not in raw:
        _, selected, _, _ = select_config_target(raw=raw, target=target)
        return (selected,)
    targets: object = raw.get(TARGETS_CONFIG_KEY)
    if not isinstance(targets, dict) or not targets:
        _ = select_config_target(raw=raw, target=None)
        raise ConfigValidationError("Config key targets must define at least one named target.")
    names: tuple[str, ...] = tuple(sorted(str(name) for name in targets))
    for name in names:
        _ = select_config_target(raw=raw, target=name)
    return names


def _normalize_target_root(*, name: str, value: str) -> str:
    windows_path: PureWindowsPath = PureWindowsPath(value)
    configured: PurePosixPath = PurePosixPath(
        value.replace(_windows_path_separator, PATH_SEPARATOR)
    )
    if configured.is_absolute() or windows_path.is_absolute() or windows_path.drive:
        raise ConfigValidationError(f"Target {name} root {value!r} must be repository-relative.")
    parts: list[str] = []
    for part in configured.parts:
        if part in {_empty_string, _current_path_part}:
            continue
        if part == _parent_path_part:
            if not parts:
                raise ConfigValidationError(
                    f"Target {name} root {value!r} must not escape the repository."
                )
            _ = parts.pop()
            continue
        parts.append(part)
    return PurePosixPath(*parts).as_posix() if parts else DEFAULT_TARGET_ROOT


def _validate_top_level_keys(*, raw: Mapping[str, object]) -> None:
    unknown_keys: set[str] = set(raw) - set(CONFIG_TOP_LEVEL_KEYS)
    if unknown_keys:
        names: str = ", ".join(sorted(unknown_keys))
        raise ConfigValidationError(f"Unknown config key(s): {names}.")


def _validate_rule_options_shape(*, value: object) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ConfigValidationError("Config key rule_options must be a table.")
    for code, options in value.items():
        if not isinstance(code, str) or not isinstance(options, dict):
            raise ConfigValidationError("Config key rule_options must contain rule-code tables.")


def _validate_cache(*, value: object) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ConfigValidationError("Config key cache must be a table.")
    typed_value: dict[object, object] = cast(dict[object, object], value)
    unknown_keys: set[object] = set(typed_value) - {
        CACHE_ENABLED_CONFIG_KEY,
        CACHE_REQUIRE_CACHEABLE_CONFIG_KEY,
    }
    if unknown_keys:
        names: str = ", ".join(sorted(str(key) for key in unknown_keys))
        raise ConfigValidationError(f"Unknown cache config key(s): {names}.")
    if CACHE_ENABLED_CONFIG_KEY in typed_value and not isinstance(
        typed_value[CACHE_ENABLED_CONFIG_KEY], bool
    ):
        raise ConfigValidationError("Config key cache.enabled must be a boolean.")
    if CACHE_REQUIRE_CACHEABLE_CONFIG_KEY in typed_value and not isinstance(
        typed_value[CACHE_REQUIRE_CACHEABLE_CONFIG_KEY], bool
    ):
        raise ConfigValidationError("Config key cache.require_cacheable must be a boolean.")


def _validate_skills(*, value: object) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ConfigValidationError("Config key skills must be a table.")
    typed_value: dict[object, object] = cast(dict[object, object], value)
    unknown_keys: set[object] = set(typed_value) - SKILLS_CONFIG_KEYS
    if unknown_keys:
        names: str = ", ".join(sorted(str(key) for key in unknown_keys))
        raise ConfigValidationError(f"Unknown skills config key(s): {names}.")
    name: object = typed_value.get(SKILLS_NAME_CONFIG_KEY)
    if not isinstance(name, str) or not name.strip():
        raise ConfigValidationError("Config key skills.name must be a non-empty string.")


def _validate_evaluation(*, value: object) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ConfigValidationError("Config key evaluation must be a table.")
    typed_value: dict[object, object] = cast(dict[object, object], value)
    unknown_keys: set[object] = set(typed_value) - EVALUATION_CONFIG_KEYS
    if unknown_keys:
        names: str = ", ".join(sorted(str(key) for key in unknown_keys))
        raise ConfigValidationError(f"Unknown evaluation config key(s): {names}.")
    for key in EVALUATION_CONFIG_KEYS:
        if key not in typed_value:
            continue
        patterns: tuple[str, ...] = _validate_string_sequence(
            name=f"evaluation.{key}", value=typed_value[key]
        )
        if not patterns:
            raise ConfigValidationError(f"Config key evaluation.{key} must not be empty.")
        for pattern in patterns:
            _validate_path_pattern(pattern=pattern, owner=f"Evaluation {key}")


def _validate_string_sequence(*, name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ConfigError(f"Config key {name} must be a list of strings.")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ConfigValidationError(f"Config key {name} must contain non-empty strings.")
        result.append(item)
    return tuple(result)


def _validate_test_scopes(*, value: object) -> None:
    if value is None:
        return
    scopes: tuple[str, ...] = _validate_string_sequence(name="test_scopes", value=value)
    if not scopes:
        raise ConfigValidationError("Config key test_scopes must not be empty.")
    if len(set(scopes)) != len(scopes):
        raise ConfigValidationError("Config key test_scopes must not contain duplicates.")
    for scope in scopes:
        if not TEST_SCOPE_PATTERN.fullmatch(scope):
            raise ConfigValidationError(
                f"Config key test_scopes must contain single lowercase path segments: {scope!r}."
            )


def _validate_optional_string_sequence(*, name: str, value: object) -> None:
    if value is None:
        return
    _ = _validate_string_sequence(name=name, value=value)


def _validate_no_nested_paths(*, name: str, paths: tuple[str, ...]) -> None:
    normalized_paths: tuple[tuple[str, ...], ...] = tuple(
        PurePosixPath(path).parts for path in paths
    )
    for index, parent in enumerate(normalized_paths):
        for offset, child in enumerate(normalized_paths[index + 1 :]):
            if _path_parts_nested(first=parent, second=child):
                raise ConfigError(
                    _nested_paths_message(
                        name=name,
                        first=paths[index],
                        second=paths[index + 1 + offset],
                        first_is_outer=len(parent) <= len(child),
                    )
                )


def _nested_paths_message(*, name: str, first: str, second: str, first_is_outer: bool) -> str:
    outer, inner = (first, second) if first_is_outer else (second, first)
    if outer == inner:
        return f"Config key {name} must not contain duplicate paths: {outer!r}."
    return f"Config key {name} must not contain nested paths: {outer!r} contains {inner!r}."


def _path_parts_nested(*, first: tuple[str, ...], second: tuple[str, ...]) -> bool:
    shortest_length: int = min(len(first), len(second))
    return first[:shortest_length] == second[:shortest_length]


def _validate_selection(*, name: str, value: object) -> None:
    if value is None:
        return
    entries: tuple[str, ...] = _validate_string_sequence(name=name, value=value)
    for entry in entries:
        if not is_rule_selector(entry):
            raise ConfigValidationError(f"Config key {name} contains invalid selector {entry}.")


def _validate_thresholds(*, value: object, owner: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ConfigValidationError(f"Config key {owner} must be a table of integer thresholds.")
    valid_thresholds: set[str] = {threshold.value for threshold in Threshold}
    for key, threshold_value in value.items():
        if not isinstance(key, str) or key not in valid_thresholds:
            raise ConfigValidationError(f"Unknown threshold key in {owner}: {key}.")
        if type(threshold_value) is not int:
            raise ConfigValidationError(f"Threshold {key} in {owner} must be an integer.")
        if threshold_value < 0:
            raise ConfigValidationError(f"Threshold {key} in {owner} must be non-negative.")
        if threshold_value > MAX_THRESHOLD_VALUE:
            raise ConfigValidationError(f"Threshold {key} in {owner} is too large.")


def _validate_role_thresholds(*, value: object) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ConfigValidationError("Config key roles must be a table of role threshold tables.")
    for role_name, thresholds in value.items():
        if not isinstance(role_name, str) or role_name not in CONFIG_ROLE_NAMES:
            raise ConfigValidationError(f"Unknown role name in roles: {role_name}.")
        _validate_thresholds(value=thresholds, owner=f"roles.{role_name}")


def _validate_threshold_overrides(*, value: object) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise ConfigValidationError("Config key threshold_overrides must be an array of tables.")
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != THRESHOLD_OVERRIDE_KEYS:
            raise ConfigValidationError(
                "Each threshold_overrides entry must define only paths, thresholds, and reason."
            )
        paths: tuple[str, ...] = _validate_string_sequence(
            name="threshold_overrides.paths", value=entry.get("paths")
        )
        if not paths:
            raise ConfigValidationError("Threshold override paths must not be empty.")
        for pattern in paths:
            _validate_path_pattern(pattern=pattern, owner="Threshold override path")
        reason: object = entry.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ConfigValidationError("Threshold override reason must be non-empty.")
        thresholds: object = entry.get("thresholds")
        if not isinstance(thresholds, dict) or not thresholds:
            raise ConfigValidationError(
                "Threshold override thresholds must be a non-empty inline table."
            )
        _validate_thresholds(value=thresholds, owner="threshold_overrides.thresholds")


def _validate_rule_ignores(*, value: object) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise ConfigValidationError("Config key rule_ignores must be an array of tables.")
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != RULE_IGNORE_KEYS:
            raise ConfigValidationError(
                "Each rule_ignores entry must define only rules, paths, and reason."
            )
        rules: tuple[str, ...] = _validate_string_sequence(
            name="rule_ignores.rules", value=entry.get("rules")
        )
        if not rules:
            raise ConfigValidationError("Rule ignore selectors must not be empty.")
        for selector in rules:
            if not is_rule_selector(selector):
                raise ConfigValidationError(
                    f"Config key rule_ignores.rules contains invalid selector {selector}."
                )
        paths: tuple[str, ...] = _validate_string_sequence(
            name="rule_ignores.paths", value=entry.get("paths")
        )
        if not paths:
            raise ConfigValidationError("Rule ignore paths must not be empty.")
        for pattern in paths:
            _validate_path_pattern(pattern=pattern, owner="Rule ignore path")
        reason: object = entry.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ConfigValidationError("Rule ignore reason must be non-empty.")


def _validate_path_pattern(*, pattern: str, owner: str) -> None:
    parsed: PurePosixPath = PurePosixPath(pattern)
    malformed: bool = (
        pattern.startswith("/")
        or pattern.endswith("/")
        or DOUBLE_PATH_SEPARATOR in pattern
        or any(character in pattern for character in {"?", "[", "]"})
        or any(
            RECURSIVE_GLOB in part and part != RECURSIVE_GLOB
            for part in pattern.split(PATH_SEPARATOR)
        )
        or f"{RECURSIVE_GLOB}{PATH_SEPARATOR}{RECURSIVE_GLOB}" in pattern
    )
    if (
        parsed.is_absolute()
        or _windows_path_separator in pattern
        or pattern != parsed.as_posix()
        or malformed
        or any(part in {_current_path_part, _parent_path_part} for part in parsed.parts)
    ):
        raise ConfigValidationError(f"{owner} must be a repository-relative POSIX glob: {pattern}.")


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


def _validate_rule_exceptions(*, value: object) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise ConfigValidationError("Config key rule_exceptions must be an array of tables.")
    seen: set[tuple[str, str, str | None]] = set()
    for entry in value:
        seen = _validate_rule_exception_entry(entry=entry, seen=seen)


def _validate_rule_exception_entry(
    *, entry: object, seen: set[tuple[str, str, str | None]]
) -> set[tuple[str, str, str | None]]:
    if not isinstance(entry, dict):
        raise ConfigValidationError("Each rule_exceptions entry must be a table.")
    typed_entry: dict[object, object] = cast(dict[object, object], entry)
    required_keys: set[str] = {"rule", "path", "reason"}
    allowed_keys: set[str] = {*required_keys, RULE_EXCEPTION_SYMBOLS_CONFIG_KEY}
    if not required_keys.issubset(typed_entry) or not set(typed_entry).issubset(allowed_keys):
        raise ConfigValidationError(
            "Each rule_exceptions entry must define rule, path, and reason, with optional symbols."
        )
    rule: str = _exception_string(entry=typed_entry, key="rule")
    path: str = _exception_string(entry=typed_entry, key="path")
    reason: str = _exception_string(entry=typed_entry, key="reason")
    if reason.strip() == _empty_string:
        raise ConfigValidationError("Rule exception reason must be non-empty.")
    if not is_rule_code(rule):
        raise ConfigValidationError(f"Rule exception must use one exact rule code: {rule}.")
    _validate_exception_path(path)
    if RULE_EXCEPTION_SYMBOLS_CONFIG_KEY not in typed_entry:
        key: tuple[str, str, str | None] = (rule, path, None)
        if key in seen:
            raise ConfigValidationError(
                f"Duplicate file-level rule exception for {rule} at {path}."
            )
        seen.add(key)
        return seen
    symbols: tuple[str, ...] = _validate_string_sequence(
        name="rule_exceptions.symbols", value=typed_entry[RULE_EXCEPTION_SYMBOLS_CONFIG_KEY]
    )
    if not symbols:
        raise ConfigValidationError(
            "Rule exception symbols must not be empty; omit symbols for a file-level exception."
        )
    for symbol in symbols:
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?", symbol) is None:
            raise ConfigValidationError(f"Malformed qualified rule exception symbol: {symbol}.")
        key = (rule, path, symbol)
        if key in seen:
            raise ConfigValidationError(f"Duplicate rule exception for {rule} at {path}: {symbol}.")
        seen.add(key)
    return seen


def _exception_string(*, entry: Mapping[object, object], key: str) -> str:
    value: object = entry.get(key)
    if not isinstance(value, str) or value == _empty_string:
        raise ConfigValidationError(f"Rule exception {key} must be a non-empty string.")
    return value


def _validate_exception_path(path: str) -> None:
    parsed: PurePosixPath = PurePosixPath(path)
    if (
        parsed.is_absolute()
        or _windows_path_separator in path
        or any(character in path for character in _glob_characters)
        or path != parsed.as_posix()
        or any(part in {_current_path_part, _parent_path_part} for part in parsed.parts)
        or parsed.suffix != _python_file_suffix
    ):
        raise ConfigValidationError(
            f"Rule exception path must be one exact repository-relative POSIX Python file: {path}."
        )
