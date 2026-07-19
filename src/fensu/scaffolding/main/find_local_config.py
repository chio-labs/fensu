"""Find a safe configuration source in the current repository only."""

from pathlib import Path

from fensu.scaffolding._helpers.planning import find_local_config as _find_local_config


def find_local_config(*, repository: Path) -> Path | None:
    """Return a local Fensu config while rejecting a local config symlink."""

    return _find_local_config(repository=repository)
