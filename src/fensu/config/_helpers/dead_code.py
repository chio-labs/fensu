"""Use the shared native grammar for reachability configuration."""

import json

from fensu.config.exceptions import ConfigValidationError
from fensu.config.models import DeadCodeConfig, DeadCodeRoot


def parse_dead_code(value: object) -> DeadCodeConfig:
    """Validate unknown keys, pattern syntax, types, and required reasons."""

    if value is None:
        return DeadCodeConfig()
    import fensu._native as native

    try:
        enabled, roots = native.parse_dead_code_config(json.dumps(value))
    except ValueError as error:
        raise ConfigValidationError(str(error)) from error
    return DeadCodeConfig(
        enabled=enabled,
        roots=tuple(
            DeadCodeRoot(tuple(modules), tuple(symbols), reason)
            for modules, symbols, reason in roots
        ),
    )
