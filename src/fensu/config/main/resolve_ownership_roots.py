"""Resolve configured ownership-root selectors to concrete target paths."""

from pathlib import Path

from fensu.config.exceptions import ConfigError
from fensu.config.main.expand_path_pattern import expand_path_pattern
from fensu.config.models import Config
from fensu.config.types import AnalyzerId


def resolve_ownership_roots(*, config: Config, project_root: Path) -> tuple[str, ...]:
    """Return deterministic concrete ownership roots for one analyzer target."""

    if not config.ownership_roots:
        if config.analyzer in {AnalyzerId.TYPESCRIPT, AnalyzerId.SVELTE}:
            return tuple(f"{root}/lib" for root in config.roots)
        if config.analyzer is AnalyzerId.RUST:
            return ()
        return config.roots
    resolved: set[str] = set()
    for pattern in config.ownership_roots:
        matches: tuple[Path, ...] = _expanded_directories(
            pattern=pattern, project_root=project_root
        )
        if not matches:
            raise ConfigError(
                f"Configured ownership root pattern matched no directories: {pattern}"
            )
        resolved.update(path.relative_to(project_root).as_posix() for path in matches)
    return tuple(sorted(resolved))


def _expanded_directories(*, pattern: str, project_root: Path) -> tuple[Path, ...]:
    directories: set[Path] = set()
    for expanded in expand_path_pattern(pattern=pattern):
        for path in project_root.glob(expanded):
            if path.is_dir():
                directories.add(path)
    return tuple(sorted(directories))
