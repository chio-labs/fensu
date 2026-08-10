"""Repository-relative POSIX path-pattern matching shared by path-scoped config."""

from __future__ import annotations

import re
from functools import cache

from fensu.config.constants import PATH_SEPARATOR, RECURSIVE_GLOB, SINGLE_COMPONENT_GLOB
from fensu.config.exceptions import ConfigValidationError

_MAX_EXPANDED_PATTERNS: int = 256
_MIN_BRACE_ALTERNATIVES: int = 2
_OPENING_BRACE: str = "{"
_CLOSING_BRACE: str = "}"
_ALTERNATIVE_SEPARATOR: str = ","


def path_pattern_matches(*, pattern: str, path: str) -> bool:
    """Return whether one normalized repository-relative path matches a glob."""

    return any(
        _compiled_pattern(expanded).fullmatch(path) is not None
        for expanded in expand_path_pattern(pattern=pattern)
    )


def matches_any_path_pattern(*, patterns: tuple[str, ...], path: str) -> bool:
    """Return whether any configured path pattern matches one repository path."""

    return any(path_pattern_matches(pattern=pattern, path=path) for pattern in patterns)


@cache
def path_pattern_specificity(pattern: str) -> tuple[int, int, int, int]:
    """Return literal-segment, literal-character, globstar, and wildcard specificity."""

    segments: tuple[str, ...] = tuple(pattern.split(PATH_SEPARATOR))
    literal_segments: int = sum(SINGLE_COMPONENT_GLOB not in segment for segment in segments)
    literal_characters: int = sum(
        character not in {SINGLE_COMPONENT_GLOB, PATH_SEPARATOR} for character in pattern
    )
    globstars: int = sum(segment == RECURSIVE_GLOB for segment in segments)
    wildcards: int = sum(
        segment.count(SINGLE_COMPONENT_GLOB) for segment in segments if segment != RECURSIVE_GLOB
    )
    return (literal_segments, literal_characters, -globstars, -wildcards)


def matching_path_pattern_specificity(
    *, pattern: str, path: str
) -> tuple[int, int, int, int] | None:
    """Return the strongest matching expanded alternative's specificity."""

    matching: tuple[tuple[int, int, int, int], ...] = tuple(
        path_pattern_specificity(expanded)
        for expanded in expand_path_pattern(pattern=pattern)
        if _compiled_pattern(expanded).fullmatch(path) is not None
    )
    return max(matching, default=None)


def expand_path_pattern(*, pattern: str) -> tuple[str, ...]:
    """Expand deterministic simple brace groups in one path glob."""

    return _expand_path_pattern(pattern)


@cache
def _expand_path_pattern(pattern: str) -> tuple[str, ...]:
    pending: list[str] = [pattern]
    expanded: list[str] = []
    while pending:
        candidate: str = pending.pop()
        bounds: tuple[int, int] | None = _group_bounds(candidate=candidate, original=pattern)
        if bounds is None:
            expanded.append(candidate)
            if len(expanded) > _MAX_EXPANDED_PATTERNS:
                raise ConfigValidationError(_expansion_limit_error(pattern=pattern))
            continue
        start, end = bounds
        alternatives: tuple[str, ...] = _group_alternatives(
            group=candidate[start + 1 : end], original=pattern
        )
        if len(pending) + len(expanded) + len(alternatives) > _MAX_EXPANDED_PATTERNS:
            raise ConfigValidationError(_expansion_limit_error(pattern=pattern))
        pending.extend(
            f"{candidate[:start]}{alternative}{candidate[end + 1 :]}"
            for alternative in reversed(alternatives)
        )
    return tuple(expanded)


def _group_bounds(*, candidate: str, original: str) -> tuple[int, int] | None:
    start: int | None = None
    depth: int = 0
    for index, character in enumerate(candidate):
        if character == _OPENING_BRACE:
            start = index if start is None else start
            depth += 1
        elif character == _CLOSING_BRACE:
            if depth == 0:
                raise ConfigValidationError(
                    f"Path glob contains an unmatched closing brace: {original}."
                )
            depth -= 1
            if depth == 0:
                return (start if start is not None else index, index)
    if start is not None:
        raise ConfigValidationError(f"Path glob contains an unmatched opening brace: {original}.")
    return None


def _group_alternatives(*, group: str, original: str) -> tuple[str, ...]:
    alternatives: list[str] = []
    start: int = 0
    depth: int = 0
    for index, character in enumerate(group):
        if character == _OPENING_BRACE:
            depth += 1
        elif character == _CLOSING_BRACE:
            depth -= 1
        elif character == _ALTERNATIVE_SEPARATOR and depth == 0:
            alternatives.append(group[start:index])
            start = index + 1
    alternatives.append(group[start:])
    if len(alternatives) < _MIN_BRACE_ALTERNATIVES or any(
        not alternative for alternative in alternatives
    ):
        raise ConfigValidationError(
            f"Path glob brace groups must contain at least two non-empty alternatives: {original}."
        )
    return tuple(alternatives)


def _expansion_limit_error(*, pattern: str) -> str:
    return f"Path glob expands to more than {_MAX_EXPANDED_PATTERNS} alternatives: {pattern}."


@cache
def _compiled_pattern(pattern: str) -> re.Pattern[str]:
    return re.compile(_pattern_expression(pattern))


def _pattern_expression(pattern: str) -> str:
    parts: list[str] = []
    index: int = 0
    while index < len(pattern):
        if pattern[index : index + 2] == RECURSIVE_GLOB:
            if index + 2 < len(pattern) and pattern[index + 2] == PATH_SEPARATOR:
                parts.append("(?:.*/)?")
                index += 3
                continue
            parts.append(".*")
            index += 2
            continue
        character: str = pattern[index]
        parts.append("[^/]*" if character == SINGLE_COMPONENT_GLOB else re.escape(character))
        index += 1
    expression: str = "".join(parts)
    return expression if PATH_SEPARATOR in pattern else f"(?:.*/)?{expression}"
