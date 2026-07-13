"""Build the authoritative resolved project layout from configuration."""

from __future__ import annotations

from pathlib import Path

from strata.config.exceptions import ConfigError
from strata.config.models import Config
from strata.discovery.exceptions import RepoRootNotFoundError
from strata.discovery.models import ProjectLayout, ProjectPath, ProjectSource, RepoRoot


def build_project_layout(*, config: Config, repo_root: RepoRoot) -> ProjectLayout:
    """Resolve and validate configured paths against one repository root."""

    runtime_sources: tuple[ProjectSource, ...] = tuple(
        _project_source(value=value, repo_root=repo_root) for value in config.roots
    )
    test_roots: tuple[ProjectPath, ...] = tuple(
        _project_path(value=value, repo_root=repo_root) for value in config.tests
    )
    tooling_sources: tuple[ProjectSource, ...] = tuple(
        _project_source(value=value, repo_root=repo_root) for value in config.tooling
    )
    missing_roots: tuple[str, ...] = tuple(
        value
        for value, source in zip(config.roots, runtime_sources, strict=True)
        if not source.path.is_dir()
    )
    if missing_roots:
        names: str = ", ".join(sorted(missing_roots))
        raise RepoRootNotFoundError(f"Configured root path(s) do not exist: {names}.")
    _validate_cross_scope_roots(
        runtime_sources=runtime_sources,
        test_roots=test_roots,
        tooling_sources=tooling_sources,
    )
    _validate_import_scope_names(
        runtime_sources=runtime_sources,
        test_roots=test_roots,
        tooling_sources=tooling_sources,
    )
    return ProjectLayout(
        runtime_sources=runtime_sources,
        test_roots=test_roots,
        tooling_sources=tooling_sources,
    )


def _project_source(*, value: str, repo_root: RepoRoot) -> ProjectSource:
    project_path: ProjectPath = _project_path(value=value, repo_root=repo_root)
    return ProjectSource(
        path=project_path.path,
        relative_parts=project_path.relative_parts,
        import_root=project_path.path.parent,
        package_name=project_path.path.name,
    )


def _project_path(*, value: str, repo_root: RepoRoot) -> ProjectPath:
    configured: Path = Path(value)
    path: Path = (
        configured.resolve()
        if configured.is_absolute()
        else (repo_root.path / configured).resolve()
    )
    try:
        relative_parts: tuple[str, ...] = path.relative_to(repo_root.path).parts
    except ValueError as error:
        raise ConfigError(f"Configured path must resolve inside the repository: {value}") from error
    return ProjectPath(path=path, relative_parts=relative_parts)


def _validate_cross_scope_roots(
    *,
    runtime_sources: tuple[ProjectSource, ...],
    test_roots: tuple[ProjectPath, ...],
    tooling_sources: tuple[ProjectSource, ...],
) -> None:
    scope_paths: tuple[tuple[str, tuple[Path, ...]], ...] = (
        ("roots", tuple(source.path for source in runtime_sources)),
        ("tests", tuple(root.path for root in test_roots)),
        ("tooling", tuple(source.path for source in tooling_sources)),
    )
    for index, (owner, paths) in enumerate(scope_paths):
        for other_owner, other_paths in scope_paths[index + 1 :]:
            duplicates: set[Path] = set(paths) & set(other_paths)
            if duplicates:
                duplicate: Path = min(duplicates)
                raise ConfigError(
                    f"Configured path cannot belong to both {owner} and {other_owner}: {duplicate}"
                )


def _validate_import_scope_names(
    *,
    runtime_sources: tuple[ProjectSource, ...],
    test_roots: tuple[ProjectPath, ...],
    tooling_sources: tuple[ProjectSource, ...],
) -> None:
    runtime_packages: set[str] = {source.package_name for source in runtime_sources}
    test_packages: set[str] = {root.path.name for root in test_roots}
    tooling_packages: set[str] = {source.package_name for source in tooling_sources}
    scope_packages: tuple[tuple[str, set[str]], ...] = (
        ("Runtime", runtime_packages),
        ("test", test_packages),
        ("tooling", tooling_packages),
    )
    for index, (owner, packages) in enumerate(scope_packages):
        for other_owner, other_packages in scope_packages[index + 1 :]:
            duplicates: set[str] = packages & other_packages
            if duplicates:
                names: str = ", ".join(sorted(duplicates))
                raise ConfigError(
                    f"{owner} and {other_owner} roots must not claim the same import package: "
                    f"{names}"
                )
