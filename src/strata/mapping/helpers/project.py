"""Resolve standalone and Strata-configured projects for call mapping."""

from __future__ import annotations

from pathlib import Path

from strata.config.exceptions import ConfigError
from strata.config.main.find_config import find_config_source
from strata.config.main.load_config import load_config
from strata.config.models import Config, ConfigSource
from strata.discovery.main.build_project_layout import build_project_layout
from strata.discovery.models import ProjectLayout, ProjectSource, RepoRoot
from strata.mapping.exceptions import MapError
from strata.mapping.models import MappingProject, MappingSource


def resolve_mapping_project(*, cwd: Path, explicit_roots: tuple[str, ...]) -> MappingProject:
    """Resolve mapping roots without requiring a Strata configuration."""

    resolved_cwd: Path = cwd.resolve()
    if explicit_roots:
        repo_root: Path = _find_project_root(resolved_cwd)
        sources: tuple[MappingSource, ...] = tuple(
            _explicit_source(value=value, cwd=resolved_cwd) for value in explicit_roots
        )
        return MappingProject(repo_root=repo_root, sources=sources)
    config_source: ConfigSource | None = _optional_config_source(resolved_cwd)
    if config_source is not None:
        return _configured_project(config_source)
    repo_root = _find_project_root(resolved_cwd)
    inferred_root: Path = repo_root / "src"
    if not inferred_root.is_dir():
        inferred_root = repo_root
    if not any(inferred_root.rglob("*.py")):
        raise MapError(f"No Python files found under inferred root: {inferred_root}")
    source: MappingSource = MappingSource(scan_path=inferred_root, import_root=inferred_root)
    return MappingProject(repo_root=repo_root, sources=(source,))


def _optional_config_source(cwd: Path) -> ConfigSource | None:
    try:
        return find_config_source(cwd)
    except ConfigError as error:
        raise MapError(str(error)) from error


def _configured_project(source: ConfigSource) -> MappingProject:
    repo_root: Path = source.path.parent.resolve()
    try:
        config: Config = load_config(repo_root)
        layout: ProjectLayout = build_project_layout(
            config=config,
            repo_root=RepoRoot(repo_root),
        )
    except ConfigError as error:
        raise MapError(str(error)) from error
    sources: tuple[MappingSource, ...] = tuple(
        _mapping_source(source) for source in layout.runtime_sources
    )
    return MappingProject(repo_root=repo_root, sources=sources)


def _mapping_source(source: ProjectSource) -> MappingSource:
    return MappingSource(scan_path=source.path, import_root=source.import_root)


def _explicit_source(*, value: str, cwd: Path) -> MappingSource:
    path: Path = Path(value)
    scan_path: Path = path.resolve() if path.is_absolute() else (cwd / path).resolve()
    if not scan_path.is_dir():
        raise MapError(f"Mapping root path does not exist: {value}")
    return MappingSource(scan_path=scan_path, import_root=scan_path)


def _find_project_root(cwd: Path) -> Path:
    for directory in (cwd, *cwd.parents):
        if (directory / ".git").exists() or (directory / "pyproject.toml").is_file():
            return directory
    return cwd
