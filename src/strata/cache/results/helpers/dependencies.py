"""Re-observe persisted project-query dependencies from lexical paths."""

from __future__ import annotations

from pathlib import Path

from strata.analysis.core.types import ProjectDependencyKind
from strata.cache.fingerprints.main.source import fingerprint_source
from strata.cache.results.helpers.paths import relative_repository_path
from strata.cache.results.helpers.validation import is_dependency_observation, is_relative_path
from strata.cache.results.models import DependencyObservation
from strata.cache.results.types import DependencyAnswer


def dependencies_are_current(
    *,
    observations: tuple[DependencyObservation, ...],
    repo_root: Path,
) -> bool:
    """Return whether every project-query answer and resolved target is unchanged."""

    return all(
        _reobserve(observation=observation, repo_root=repo_root) == observation
        for observation in observations
    )


def _reobserve(
    *,
    observation: DependencyObservation,
    repo_root: Path,
) -> DependencyObservation | None:
    if not is_dependency_observation(observation) or not is_relative_path(
        observation.query_path,
        allow_root=True,
    ):
        return None
    query_path: Path = repo_root / observation.query_path
    try:
        resolved_path: Path = query_path.resolve()
    except (OSError, RuntimeError):
        return None
    dependency_path: str | None = relative_repository_path(
        path=resolved_path,
        repo_root=repo_root,
        allow_root=True,
    )
    if dependency_path is None:
        return None
    answer: DependencyAnswer | None = _observe_answer(
        observation=observation,
        query_path=query_path,
        resolved_path=resolved_path,
        repo_root=repo_root,
    )
    if answer is None and observation.kind is not ProjectDependencyKind.SOURCE:
        return None
    return DependencyObservation(
        requester_path=observation.requester_path,
        query_path=observation.query_path,
        dependency_path=dependency_path,
        kind=observation.kind,
        answer=answer,
        pattern=observation.pattern,
        recursive=observation.recursive,
    )


def _observe_answer(
    *,
    observation: DependencyObservation,
    query_path: Path,
    resolved_path: Path,
    repo_root: Path,
) -> DependencyAnswer | None:
    if observation.kind is ProjectDependencyKind.SOURCE:
        try:
            return fingerprint_source(query_path.read_bytes()).value
        except OSError:
            return None
    if observation.kind is ProjectDependencyKind.EXISTS:
        return resolved_path.exists()
    if observation.kind is ProjectDependencyKind.IS_FILE:
        return resolved_path.is_file()
    if observation.kind is ProjectDependencyKind.IS_DIR:
        return resolved_path.is_dir()
    if observation.kind is ProjectDependencyKind.DIRECTORY_ENTRIES:
        try:
            return _relative_paths(paths=tuple(query_path.iterdir()), repo_root=repo_root)
        except OSError:
            return None
    if observation.kind is ProjectDependencyKind.GLOB and observation.pattern is not None:
        try:
            paths: tuple[Path, ...] = tuple(
                query_path.rglob(observation.pattern)
                if observation.recursive
                else query_path.glob(observation.pattern)
            )
        except OSError:
            return None
        return _relative_paths(paths=paths, repo_root=repo_root)
    return None


def _relative_paths(*, paths: tuple[Path, ...], repo_root: Path) -> tuple[str, ...] | None:
    values: list[str] = []
    for path in paths:
        value: str | None = relative_repository_path(
            path=path,
            repo_root=repo_root,
            allow_root=True,
        )
        if value is None:
            return None
        values.append(value)
    return tuple(values)
