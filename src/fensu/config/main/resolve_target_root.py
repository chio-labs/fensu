"""Resolve a selected target root inside its repository."""

from pathlib import Path

from fensu.config.constants import DEFAULT_TARGET_ROOT
from fensu.config.exceptions import ConfigError
from fensu.config.models import Config, ResolvedTargetRoot


def resolve_target_root(*, config: Config, repo_root: Path) -> ResolvedTargetRoot:
    """Return one canonical path and repository-relative target identity."""

    repository: Path = repo_root.resolve()
    target: Path = (repository / config.target_root).resolve()
    if not target.is_relative_to(repository):
        raise ConfigError(
            f"Target {config.target or '<legacy>'} root {config.target_root!r} "
            "must not escape the repository."
        )
    relative: Path = target.relative_to(repository)
    repository_relative: str = DEFAULT_TARGET_ROOT if not relative.parts else relative.as_posix()
    return ResolvedTargetRoot(path=target, repository_relative=repository_relative)
