"""Match one repository-relative path against configured POSIX globs."""

from strata.config.helpers.path_patterns import matches_any_path_pattern


def path_matches(*, patterns: tuple[str, ...], path: str) -> bool:
    """Return whether any configured path pattern matches one repository path."""

    return matches_any_path_pattern(patterns=patterns, path=path)
