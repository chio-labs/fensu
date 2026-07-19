"""Resolve deterministic project skill names and installation roots."""

from __future__ import annotations

import re
import tomllib
import unicodedata
from pathlib import Path

from fensu.agentdocs.constants import SKILL_NAME_PREFIX
from fensu.agentdocs.exceptions import SkillInstallError
from fensu.agentdocs.types import SkillInstallRoot
from fensu.config.exceptions import ConfigError
from fensu.config.models import Config, ConfigSource


def normalize_skill_identity(value: str) -> str:
    """Normalize one project identity to stable lowercase ASCII kebab-case."""

    decomposed: str = unicodedata.normalize("NFKD", value)
    ascii_value: str = decomposed.encode("ascii", "ignore").decode("ascii").lower()
    normalized: str = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    if not normalized:
        raise ConfigError(f"Skill identity {value!r} does not contain an ASCII letter or digit.")
    return normalized


def find_git_root(project_root: Path) -> Path | None:
    """Return the nearest parent with a directory or file `.git` marker."""

    for candidate in (project_root.resolve(), *project_root.resolve().parents):
        marker: Path = candidate / ".git"
        if marker.is_dir() or marker.is_file():
            return candidate
    return None


def resolve_install_root(
    *, value: str | None, project_root: Path, invocation_root: Path
) -> tuple[Path, Path | None]:
    """Resolve default, named, or path installation-root semantics."""

    resolved_project: Path = project_root.resolve()
    git_root: Path | None = find_git_root(resolved_project)
    if value is None:
        return (git_root or resolved_project), git_root
    if value == SkillInstallRoot.PROJECT:
        return resolved_project, git_root
    if value == SkillInstallRoot.GIT:
        if git_root is None:
            raise SkillInstallError(
                "--install-root git requires a parent Git repository containing .git."
            )
        return git_root, git_root
    configured: Path = Path(value).expanduser()
    explicit: Path = configured if configured.is_absolute() else invocation_root / configured
    return explicit.resolve(), git_root


def resolve_skill_name(
    *, config: Config, source: ConfigSource, project_root: Path, git_root: Path | None
) -> str:
    """Resolve configured, package, directory, then Git-relative project identity."""

    if config.skills.name is not None:
        return SKILL_NAME_PREFIX + normalize_skill_identity(config.skills.name)
    pyproject_name: str | None = _nearest_project_name(project_root)
    if pyproject_name is not None:
        try:
            return SKILL_NAME_PREFIX + normalize_skill_identity(pyproject_name)
        except ConfigError:
            pass
    try:
        return SKILL_NAME_PREFIX + normalize_skill_identity(source.path.parent.name)
    except ConfigError:
        fallback: str = _git_relative_fallback(project_root=project_root, git_root=git_root)
        return SKILL_NAME_PREFIX + normalize_skill_identity(fallback)


def project_prefix(*, project_root: Path, install_root: Path) -> str:
    """Return a POSIX project prefix when installation occurs at an ancestor."""

    try:
        relative: Path = project_root.resolve().relative_to(install_root.resolve())
    except ValueError:
        return ""
    return relative.as_posix() if relative.parts else ""


def _nearest_project_name(project_root: Path) -> str | None:
    for directory in (project_root.resolve(), *project_root.resolve().parents):
        path: Path = directory / "pyproject.toml"
        if not path.is_file():
            continue
        try:
            with path.open("rb") as file:
                data: object = tomllib.load(file)
        except tomllib.TOMLDecodeError as error:
            raise ConfigError(
                f"Could not parse {path} while resolving skill identity: {error}"
            ) from error
        if not isinstance(data, dict):
            continue
        project: object = data.get("project")
        if isinstance(project, dict):
            name: object = project.get("name")
            if isinstance(name, str) and name:
                return name
    return None


def _git_relative_fallback(*, project_root: Path, git_root: Path | None) -> str:
    if git_root is None:
        return project_root.resolve().as_posix()
    relative: Path = project_root.resolve().relative_to(git_root)
    return relative.as_posix() or git_root.name
