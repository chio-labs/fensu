"""Helpers for dependency re-observation tests."""

from collections.abc import Callable, Iterator
from pathlib import Path

from strata.analysis.types import ProjectDependencyKind
from strata.cache.results.models import DependencyObservation


def _create_directory(path: Path) -> bool:
    path.mkdir()
    return True


def _create_file(path: Path) -> bool:
    path.write_text("value", encoding="utf-8")
    return True


def _remove_path(path: Path) -> None:
    path.unlink()


def _replace_file_with_directory(path: Path) -> None:
    path.unlink()
    path.mkdir()


def _replace_directory_with_file(path: Path) -> None:
    path.rmdir()
    path.write_text("value", encoding="utf-8")


def scalar_observation(
    *,
    repo_root: Path,
    kind: ProjectDependencyKind,
) -> DependencyObservation:
    """Create one scalar query target and its initial observation."""

    path: Path = repo_root / "target"
    setup: Callable[[Path], bool] = {
        ProjectDependencyKind.IS_DIR: _create_directory,
        ProjectDependencyKind.EXISTS: _create_file,
        ProjectDependencyKind.IS_FILE: _create_file,
    }[kind]
    answer: bool = setup(path)
    return DependencyObservation(
        requester_path="src/pkg/models.py",
        query_path="target",
        dependency_path="target",
        kind=kind,
        answer=answer,
    )


def mutate_scalar_target(*, repo_root: Path, kind: ProjectDependencyKind) -> None:
    """Change one scalar query answer without changing its lexical path."""

    path: Path = repo_root / "target"
    mutation: Callable[[Path], None] = {
        ProjectDependencyKind.EXISTS: _remove_path,
        ProjectDependencyKind.IS_FILE: _replace_file_with_directory,
        ProjectDependencyKind.IS_DIR: _replace_directory_with_file,
    }[kind]
    mutation(path)


def glob_answer(*, repo_root: Path, recursive: bool) -> tuple[str, ...]:
    """Return the current ordered Python matches using project-query semantics."""

    package: Path = repo_root / "pkg"
    glob_method: Callable[[str], Iterator[Path]] = {
        False: package.glob,
        True: package.rglob,
    }[recursive]
    paths: tuple[Path, ...] = tuple(glob_method("*.py"))
    return tuple(path.relative_to(repo_root).as_posix() for path in paths)


def add_glob_match(*, repo_root: Path, recursive: bool) -> None:
    """Add one match visible only at the selected glob depth."""

    relative_path: str = {False: "pkg/later.py", True: "pkg/nested/later.py"}[recursive]
    path: Path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
