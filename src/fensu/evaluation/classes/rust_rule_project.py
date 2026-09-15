"""Requester-bound common project facts for hosted Rust custom rules."""

from __future__ import annotations

from pathlib import Path

from fensu.analysis.models import ProjectDependency
from fensu.evaluation.classes.rust_dependency_observer import RustDependencyObserver
from fensu.evaluation.exceptions import ProjectContextUnavailableError
from fensu.rules.authoring.models import ProjectPath, ProjectTree


class RustRuleProjectView:
    """Expose deterministic tree facts and dependency observations."""

    def __init__(
        self,
        *,
        root: Path,
        tree: ProjectTree,
        requester: str,
        observations: list[dict[str, str]],
    ) -> None:
        self._root: Path = root
        self._requester: str = requester
        self._observations: list[dict[str, str]] = observations
        observer: RustDependencyObserver = RustDependencyObserver(
            requester=requester, observations=observations
        )
        self._tree: ProjectTree = tree.observed(observer)

    @property
    def tree(self) -> ProjectTree:
        """Return immutable authoritative Rust discovery facts."""

        return self._tree

    def absolute_path(self, value: ProjectPath | str) -> Path:
        """Resolve one confined project path beneath the analyzed Cargo root."""

        path: ProjectPath = value if isinstance(value, ProjectPath) else ProjectPath(value)
        absolute: Path = (self._root / path.value).resolve()
        if not absolute.is_relative_to(self._root):
            raise ProjectContextUnavailableError("Rust project path escapes the analyzed project")
        return absolute

    def dependencies(self) -> tuple[ProjectDependency, ...]:
        """Return public dependency evidence observed by the hosted rules."""

        return tuple(
            ProjectDependency(
                requester=self._root / item["requester"],
                query_path=self._root / item["query"],
                dependency=self._root / item["query"],
                kind=item["kind"],
                answer=item["answer"],
            )
            for item in self._observations
        )

    def dependencies_for(self, *, requester: Path | None = None) -> tuple[ProjectDependency, ...]:
        """Return dependency evidence for the active or explicit requester."""

        expected: str = (
            self._requester if requester is None else requester.relative_to(self._root).as_posix()
        )
        return tuple(
            item for item in self.dependencies() if item.requester == self._root / expected
        )
