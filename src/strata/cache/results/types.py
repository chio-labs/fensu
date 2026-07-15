"""Persistent evaluation-result record types."""

from strata.analysis.types import ProjectDependencyKind

type DependencyAnswer = None | bool | str | tuple[str, ...]
type DependencyAnswerCache = dict[int, tuple[str, ...]]
type DependencyPathCache = dict[tuple[int, bool], str | None]
type DependencyReferenceKey = tuple[str, ProjectDependencyKind, str | None, bool]
type DependencyStateKey = tuple[str, ProjectDependencyKind, str | None, bool]
type DependencyState = tuple[str, DependencyAnswer]
type DependencyStateCache = dict[DependencyStateKey, DependencyState | None]
