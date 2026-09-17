"""Build the authoritative resolved project layout from configuration."""

from __future__ import annotations

from pathlib import Path

from fensu.config.exceptions import ConfigError
from fensu.config.main.expand_path_pattern import expand_path_pattern
from fensu.config.models import Config
from fensu.discovery.constants import ROLE_DIR_NAMES
from fensu.discovery.exceptions import RepoRootNotFoundError
from fensu.discovery.models import (
    OwnershipRoot,
    ProjectLayout,
    ProjectPath,
    ProjectSource,
    RepoRoot,
)

_GLOB_CHARACTERS: frozenset[str] = frozenset("*?[]")


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
    ownership_roots: tuple[OwnershipRoot, ...] = _ownership_roots(
        configured=config.ownership_roots,
        runtime_sources=runtime_sources,
        repo_root=repo_root,
    )
    return ProjectLayout(
        runtime_sources=runtime_sources,
        test_roots=test_roots,
        tooling_sources=tooling_sources,
        ownership_roots=ownership_roots,
    )


def _ownership_roots(
    *,
    configured: tuple[str, ...],
    runtime_sources: tuple[ProjectSource, ...],
    repo_root: RepoRoot,
) -> tuple[OwnershipRoot, ...]:
    if not configured:
        return tuple(
            OwnershipRoot(
                path=source.path,
                relative_parts=source.relative_parts,
                declaration=f"roots[{index}]",
            )
            for index, source in enumerate(runtime_sources)
        )
    matches: dict[Path, list[tuple[tuple[int, int, int], int, str]]] = {}
    for index, pattern in enumerate(configured):
        concrete: tuple[Path, ...] = _expanded_directories(pattern=pattern, root=repo_root.path)
        if not concrete:
            raise ConfigError(
                f"Configured ownership root pattern matched no directories: {pattern}"
            )
        specificity: tuple[int, int, int] = _pattern_specificity(pattern)
        for path in concrete:
            source: ProjectSource | None = next(
                (
                    source
                    for source in runtime_sources
                    if path == source.path or path.is_relative_to(source.path)
                ),
                None,
            )
            if source is None:
                raise ConfigError(
                    f"Configured ownership root must resolve beneath a runtime root: {pattern}"
                )
            relative_to_source: tuple[str, ...] = path.relative_to(source.path).parts
            if any(part in ROLE_DIR_NAMES for part in relative_to_source):
                raise ConfigError(f"Configured ownership root crosses a role directory: {pattern}")
            if not any(candidate.is_file() for candidate in path.rglob("*.py")):
                raise ConfigError(f"Configured ownership root contains no Python files: {path}")
            matches.setdefault(path, []).append((specificity, index, pattern))
    roots: list[OwnershipRoot] = []
    selected_declarations: set[int] = set()
    for path, declarations in sorted(matches.items()):
        best_specificity: tuple[int, int, int] = max(item[0] for item in declarations)
        best: list[tuple[tuple[int, int, int], int, str]] = [
            item for item in declarations if item[0] == best_specificity
        ]
        if len(best) > 1:
            patterns: str = ", ".join(sorted(item[2] for item in best))
            raise ConfigError(
                f"Ownership root has equal-specificity declarations for {path}: {patterns}"
            )
        _, index, pattern = best[0]
        selected_declarations.add(index)
        roots.append(
            OwnershipRoot(
                path=path,
                relative_parts=path.relative_to(repo_root.path).parts,
                declaration=f"ownership_roots[{index}] ({pattern})",
            )
        )
    unused_declarations: tuple[str, ...] = tuple(
        pattern for index, pattern in enumerate(configured) if index not in selected_declarations
    )
    if unused_declarations:
        names: str = ", ".join(unused_declarations)
        raise ConfigError(f"Configured ownership root declaration is unused: {names}")
    resolved: tuple[OwnershipRoot, ...] = tuple(roots)
    _validate_ownership_root_usage(roots=resolved, runtime_sources=runtime_sources)
    return resolved


def _pattern_specificity(pattern: str) -> tuple[int, int, int]:
    literal_parts: int = 0
    literal_characters: int = 0
    glob_characters: int = 0
    for part in Path(pattern).parts:
        part_contains_glob: bool = False
        for character in part:
            if character in _GLOB_CHARACTERS:
                part_contains_glob = True
                glob_characters += 1
            else:
                literal_characters += 1
        if not part_contains_glob:
            literal_parts += 1
    return literal_parts, literal_characters, -glob_characters


def _expanded_directories(*, pattern: str, root: Path) -> tuple[Path, ...]:
    directories: set[Path] = set()
    for expanded in expand_path_pattern(pattern=pattern):
        for path in root.glob(expanded):
            if path.is_dir():
                directories.add(path.resolve())
    return tuple(sorted(directories))


def _validate_ownership_root_usage(
    *, roots: tuple[OwnershipRoot, ...], runtime_sources: tuple[ProjectSource, ...]
) -> None:
    used: set[Path] = set()
    for source in runtime_sources:
        for path in source.path.rglob("*.py"):
            matches: tuple[OwnershipRoot, ...] = tuple(
                root for root in roots if path.is_relative_to(root.path)
            )
            if not matches:
                continue
            root: OwnershipRoot = max(matches, key=lambda item: len(item.path.parts))
            used.add(root.path)
    unused: tuple[OwnershipRoot, ...] = tuple(root for root in roots if root.path not in used)
    if unused:
        paths: str = ", ".join(str(root.path) for root in unused)
        raise ConfigError(f"Configured ownership root is unused: {paths}")


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
