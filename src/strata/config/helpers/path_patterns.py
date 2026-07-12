"""Repository-relative POSIX path-pattern matching shared by path-scoped config."""

from __future__ import annotations

import re

from strata.config.constants import PATH_SEPARATOR, RECURSIVE_GLOB, SINGLE_COMPONENT_GLOB


def path_pattern_matches(*, pattern: str, path: str) -> bool:
    """Return whether one normalized repository-relative path matches a glob."""

    return re.fullmatch(_pattern_expression(pattern), path) is not None


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
