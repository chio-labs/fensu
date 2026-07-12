"""Persistent evaluation-result record types."""

from strata.analysis.core.types import ProjectDependencyKind

type DependencyAnswer = None | bool | str | tuple[str, ...]
type DependencyStateKey = tuple[str, ProjectDependencyKind, str | None, bool]
type DependencyState = tuple[str, DependencyAnswer]
type DependencyStateCache = dict[DependencyStateKey, DependencyState | None]
