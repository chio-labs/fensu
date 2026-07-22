"""Expose repository path-pattern matching through the config boundary."""

from __future__ import annotations

from fensu.config._helpers.path_patterns import matches_any_path_pattern


def matches_path_pattern(*, patterns: tuple[str, ...], path: str) -> bool:
    """Return whether any configured path pattern matches a repository path."""

    return matches_any_path_pattern(patterns=patterns, path=path)
