"""Re-observe persisted project-query dependencies from lexical paths."""

from __future__ import annotations

from pathlib import Path

from strata.analysis.classes.query_observer import QueryObserver
from strata.analysis.main.observe_repository_contexts import observe_repository_contexts
from strata.analysis.main.observe_repository_python_globs import observe_repository_python_globs
from strata.analysis.main.observe_repository_stats import observe_repository_stats
from strata.analysis.models import (
    RepositoryContextAnswer,
    RepositoryGlobAnswer,
    RepositoryStatAnswer,
)
from strata.analysis.types import ProjectDependencyKind
from strata.cache.results._helpers.paths import relative_repository_path
from strata.cache.results._helpers.validation import is_dependency_observation, is_relative_path
from strata.cache.results.models import DependencyObservation
from strata.cache.results.types import (
    DependencyAnswer,
    DependencyState,
    DependencyStateCache,
    DependencyStateKey,
)
from strata.instrumentation.constants import (
    NATIVE_REPOSITORY_CONTEXT_BATCH_OPERATION,
    NATIVE_REPOSITORY_GLOB_BATCH_OPERATION,
    NATIVE_REPOSITORY_STAT_BATCH_OPERATION,
    OPERATION_COUNTERS,
    PROJECT_QUERY_ANSWER_ITEM_OPERATION,
    PROJECT_QUERY_CACHE_HIT_OPERATION,
    PROJECT_QUERY_CACHE_MISS_OPERATION,
    PROJECT_QUERY_DIRECTORY_ENTRIES_OPERATION,
    PROJECT_QUERY_EXISTS_OPERATION,
    PROJECT_QUERY_GLOB_OPERATION,
    PROJECT_QUERY_IS_DIR_OPERATION,
    PROJECT_QUERY_IS_FILE_OPERATION,
    PROJECT_QUERY_OBSERVATION_OPERATION,
    PROJECT_QUERY_PYTHON_ANCHOR_OPERATION,
    PROJECT_QUERY_SOURCE_OPERATION,
)

_OBSERVER: QueryObserver = QueryObserver()
_stat_kinds: frozenset[ProjectDependencyKind] = frozenset(
    {
        ProjectDependencyKind.EXISTS,
        ProjectDependencyKind.IS_FILE,
        ProjectDependencyKind.IS_DIR,
    }
)
_stat_operations: dict[ProjectDependencyKind, str] = {
    ProjectDependencyKind.EXISTS: PROJECT_QUERY_EXISTS_OPERATION,
    ProjectDependencyKind.IS_FILE: PROJECT_QUERY_IS_FILE_OPERATION,
    ProjectDependencyKind.IS_DIR: PROJECT_QUERY_IS_DIR_OPERATION,
}
_python_glob_pattern: str = "*.py"
_context_kinds: frozenset[ProjectDependencyKind] = frozenset(
    {
        ProjectDependencyKind.SOURCE,
        ProjectDependencyKind.DIRECTORY_ENTRIES,
        ProjectDependencyKind.PYTHON_ANCHOR,
    }
)
_context_operations: dict[ProjectDependencyKind, str] = {
    ProjectDependencyKind.SOURCE: PROJECT_QUERY_SOURCE_OPERATION,
    ProjectDependencyKind.DIRECTORY_ENTRIES: PROJECT_QUERY_DIRECTORY_ENTRIES_OPERATION,
    ProjectDependencyKind.PYTHON_ANCHOR: PROJECT_QUERY_PYTHON_ANCHOR_OPERATION,
}


def dependencies_are_current(
    *,
    observations: tuple[DependencyObservation, ...],
    repo_root: Path,
    states: DependencyStateCache | None = None,
) -> bool:
    """Return whether every project-query answer and resolved target is unchanged."""

    active_states: DependencyStateCache = {} if states is None else states
    native_states: DependencyStateCache = _native_stat_states(
        observations=observations,
        repo_root=repo_root,
        states=active_states,
    )
    native_states.update(
        _native_glob_states(
            observations=observations,
            repo_root=repo_root,
            states=active_states,
        )
    )
    native_states.update(
        _native_context_states(
            observations=observations,
            repo_root=repo_root,
            states=active_states,
        )
    )
    active_states.update(native_states)
    for observation in observations:
        key: DependencyStateKey = _state_key(observation)
        if key in native_states:
            current: bool = native_states[key] == (
                observation.dependency_path,
                observation.answer,
            )
        else:
            current, active_states = _observation_is_current(
                observation=observation,
                repo_root=repo_root,
                states=active_states,
            )
        if not current:
            return False
    return True


def _observation_is_current(
    *,
    observation: DependencyObservation,
    repo_root: Path,
    states: DependencyStateCache,
) -> tuple[bool, DependencyStateCache]:
    key: DependencyStateKey = _state_key(observation)
    if key in states:
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_CACHE_HIT_OPERATION)
        state: DependencyState | None = states[key]
    else:
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_CACHE_MISS_OPERATION)
        reobserved: DependencyObservation | None = _reobserve(
            observation=observation,
            repo_root=repo_root,
        )
        state = None if reobserved is None else (reobserved.dependency_path, reobserved.answer)
        states[key] = state
    return state == (observation.dependency_path, observation.answer), states


def _native_stat_states(
    *,
    observations: tuple[DependencyObservation, ...],
    repo_root: Path,
    states: DependencyStateCache,
) -> DependencyStateCache:
    selected: dict[DependencyStateKey, DependencyObservation] = {}
    for observation in observations:
        key: DependencyStateKey = _state_key(observation)
        if (
            key not in states
            and observation.kind in _stat_kinds
            and is_dependency_observation(observation)
            and is_relative_path(value=observation.query_path, allow_root=True)
        ):
            selected.setdefault(key, observation)
    if not selected:
        return {}
    answers: tuple[RepositoryStatAnswer | None, ...] = observe_repository_stats(
        repo_root=repo_root,
        queries=tuple(
            (observation.query_path, observation.kind) for observation in selected.values()
        ),
    )
    observed: DependencyStateCache = {}
    for (key, observation), answer in zip(selected.items(), answers, strict=True):
        if answer is None:
            continue
        state: DependencyState = (answer.dependency_path, answer.answer)
        observed[key] = state
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_CACHE_MISS_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_OBSERVATION_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_ANSWER_ITEM_OPERATION)
        OPERATION_COUNTERS.record(operation=_stat_operations[observation.kind])
    if observed:
        OPERATION_COUNTERS.record(operation=NATIVE_REPOSITORY_STAT_BATCH_OPERATION)
    return observed


def _native_glob_states(
    *,
    observations: tuple[DependencyObservation, ...],
    repo_root: Path,
    states: DependencyStateCache,
) -> DependencyStateCache:
    selected: dict[DependencyStateKey, DependencyObservation] = {}
    for observation in observations:
        key: DependencyStateKey = _state_key(observation)
        if (
            key not in states
            and observation.kind is ProjectDependencyKind.GLOB
            and observation.pattern == _python_glob_pattern
            and is_dependency_observation(observation)
            and is_relative_path(value=observation.query_path, allow_root=True)
        ):
            selected.setdefault(key, observation)
    if not selected:
        return {}
    answers: tuple[RepositoryGlobAnswer | None, ...] = observe_repository_python_globs(
        repo_root=repo_root,
        queries=tuple(
            (observation.query_path, observation.recursive) for observation in selected.values()
        ),
    )
    observed: DependencyStateCache = {}
    for (key, _observation), answer in zip(selected.items(), answers, strict=True):
        if answer is None:
            continue
        state: DependencyState = (answer.dependency_path, answer.answer)
        observed[key] = state
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_CACHE_MISS_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_OBSERVATION_OPERATION)
        OPERATION_COUNTERS.record(
            operation=PROJECT_QUERY_ANSWER_ITEM_OPERATION,
            amount=len(answer.answer),
        )
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_GLOB_OPERATION)
    if observed:
        OPERATION_COUNTERS.record(operation=NATIVE_REPOSITORY_GLOB_BATCH_OPERATION)
    return observed


def _native_context_states(
    *,
    observations: tuple[DependencyObservation, ...],
    repo_root: Path,
    states: DependencyStateCache,
) -> DependencyStateCache:
    selected: dict[DependencyStateKey, DependencyObservation] = {}
    for observation in observations:
        key: DependencyStateKey = _state_key(observation)
        if (
            key not in states
            and observation.kind in _context_kinds
            and is_dependency_observation(observation)
            and is_relative_path(value=observation.query_path, allow_root=True)
        ):
            selected.setdefault(key, observation)
    if not selected:
        return {}
    answers: tuple[RepositoryContextAnswer | None, ...] = observe_repository_contexts(
        repo_root=repo_root,
        queries=tuple(
            (observation.query_path, observation.kind) for observation in selected.values()
        ),
    )
    observed: DependencyStateCache = {}
    for (key, observation), answer in zip(selected.items(), answers, strict=True):
        if answer is None:
            continue
        state: DependencyState = (answer.dependency_path, answer.answer)
        observed[key] = state
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_CACHE_MISS_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_OBSERVATION_OPERATION)
        OPERATION_COUNTERS.record(
            operation=PROJECT_QUERY_ANSWER_ITEM_OPERATION,
            amount=_context_answer_count(answer=answer),
        )
        OPERATION_COUNTERS.record(operation=_context_operations[observation.kind])
    if observed:
        OPERATION_COUNTERS.record(operation=NATIVE_REPOSITORY_CONTEXT_BATCH_OPERATION)
    return observed


def _context_answer_count(*, answer: RepositoryContextAnswer) -> int:
    if answer.answer is None:
        return 0
    return len(answer.answer) if isinstance(answer.answer, tuple) else 1


def _state_key(observation: DependencyObservation) -> DependencyStateKey:
    return (
        observation.query_path,
        observation.kind,
        observation.pattern,
        observation.recursive,
    )


def _reobserve(
    *,
    observation: DependencyObservation,
    repo_root: Path,
) -> DependencyObservation | None:
    if not is_dependency_observation(observation) or not is_relative_path(
        value=observation.query_path,
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
        return _OBSERVER.source_fingerprint(path=query_path)
    if observation.kind is ProjectDependencyKind.EXISTS:
        return _OBSERVER.exists(resolved_path=resolved_path)
    if observation.kind is ProjectDependencyKind.IS_FILE:
        return _OBSERVER.is_file(resolved_path=resolved_path)
    if observation.kind is ProjectDependencyKind.IS_DIR:
        return _OBSERVER.is_dir(resolved_path=resolved_path)
    if observation.kind is ProjectDependencyKind.DIRECTORY_ENTRIES:
        try:
            return _relative_paths(
                paths=_OBSERVER.directory_entries(query_path=query_path),
                repo_root=repo_root,
            )
        except OSError:
            return None
    if observation.kind is ProjectDependencyKind.GLOB and observation.pattern is not None:
        try:
            paths: tuple[Path, ...] = _OBSERVER.glob(
                query_path=query_path,
                pattern=observation.pattern,
                recursive=observation.recursive,
            )
        except OSError:
            return None
        return _relative_paths(paths=paths, repo_root=repo_root)
    if observation.kind is ProjectDependencyKind.PYTHON_ANCHOR:
        try:
            anchor: Path | None = _OBSERVER.python_anchor(query_path=query_path)
        except OSError:
            return None
        paths = () if anchor is None else (anchor,)
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
