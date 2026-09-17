"""Published config-layer path-pattern expansion entry point."""

from fensu.config._helpers.path_patterns import expand_path_pattern as _expand_path_pattern


def expand_path_pattern(*, pattern: str) -> tuple[str, ...]:
    """Expand deterministic simple brace groups in one repository-relative glob."""

    return _expand_path_pattern(pattern=pattern)
