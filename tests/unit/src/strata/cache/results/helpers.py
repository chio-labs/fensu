"""Helpers for dependency re-observation tests."""

from pathlib import Path

from strata.analysis.types import ProjectDependencyKind
from strata.cache.results.models import DependencyObservation


def scalar_observation(
    *,
    repo_root: Path,
    kind: ProjectDependencyKind,
) -> DependencyObservation:
    """Create one scalar query target and its initial observation."""

    path: Path = repo_root / "target"
    if kind is ProjectDependencyKind.IS_DIR:
        path.mkdir()
        answer: bool = True
    else:
        path.write_text("value", encoding="utf-8")
        answer = kind is not ProjectDependencyKind.IS_DIR
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
    if kind is ProjectDependencyKind.EXISTS:
        path.unlink()
    elif kind is ProjectDependencyKind.IS_FILE:
        path.unlink()
        path.mkdir()
    else:
        path.rmdir()
        path.write_text("value", encoding="utf-8")


def glob_answer(*, repo_root: Path, recursive: bool) -> tuple[str, ...]:
    """Return the current ordered Python matches using project-query semantics."""

    package: Path = repo_root / "pkg"
    paths: tuple[Path, ...] = tuple(package.rglob("*.py") if recursive else package.glob("*.py"))
    return tuple(path.relative_to(repo_root).as_posix() for path in paths)


def add_glob_match(*, repo_root: Path, recursive: bool) -> None:
    """Add one match visible only at the selected glob depth."""

    relative_path: str = "pkg/nested/later.py" if recursive else "pkg/later.py"
    path: Path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
