"""Requester-bound project and discovered-tree facts exposed through RuleContext."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fensu.discovery.models import DiscoveredTree, RepoRoot
from fensu.rules.authoring.models import ProjectPath, ProjectTree


class RuleProjectView:
    """Bind project queries to one stable rule invocation requester."""

    def __init__(self, *, tree: DiscoveredTree, analysis: Any, requester: Path) -> None:
        project_root: RepoRoot = tree.repo_root if tree.project_root is None else tree.project_root
        self._root: Path = project_root.path
        self._analysis: Any = analysis
        self._requester: Path = requester
        self.tree: ProjectTree = analysis.observed_project_tree(requester=requester)

    def analysis(
        self,
        *,
        path: ProjectPath | str | Path,
        requester: Path | None = None,
    ) -> Any:
        """Return analysis and record it against the bound or legacy requester."""

        return self._analysis.analysis(
            requester=self._bound_requester(requester),
            path=self._absolute(path=path, legacy=requester is not None),
        )

    def dataclasses(
        self,
        *,
        path: ProjectPath | str | Path,
        requester: Path | None = None,
    ) -> tuple[Any, ...]:
        """Return dataclass facts and record the source dependency."""

        return self._analysis.dataclasses(
            requester=self._bound_requester(requester),
            path=self._absolute(path=path, legacy=requester is not None),
        )

    def directory_entries(
        self,
        *,
        path: ProjectPath | str | Path,
        requester: Path | None = None,
    ) -> tuple[Path, ...]:
        """Preserve the requester-aware legacy directory query."""

        return self._analysis.directory_entries(
            requester=self._bound_requester(requester),
            path=self._absolute(path=path, legacy=requester is not None),
        )

    def module_function(
        self,
        *,
        module_name: str,
        function_name: str,
        requester: Path | None = None,
    ) -> Any:
        """Return a project function contract with requester tracking."""

        return self._analysis.module_function(
            requester=self._bound_requester(requester),
            module_name=module_name,
            function_name=function_name,
        )

    def entrypoint_modules(self, *, requester: Path | None = None) -> tuple[str, ...]:
        """Return configured entrypoint modules with requester tracking."""

        return self._analysis.entrypoint_modules(requester=self._bound_requester(requester))

    def python_anchor(
        self,
        *,
        path: ProjectPath | str | Path,
        requester: Path | None = None,
    ) -> Path | None:
        """Preserve the requester-aware legacy Python-anchor query."""

        return self._analysis.python_anchor(
            requester=self._bound_requester(requester),
            path=self._absolute(path=path, legacy=requester is not None),
        )

    def exists(
        self,
        *,
        path: ProjectPath | str | Path,
        requester: Path | None = None,
    ) -> bool:
        """Return whether a path exists with requester tracking."""

        return self._analysis.exists(
            requester=self._bound_requester(requester),
            path=self._absolute(path=path, legacy=requester is not None),
        )

    def is_dir(
        self,
        *,
        path: ProjectPath | str | Path,
        requester: Path | None = None,
    ) -> bool:
        """Return whether a path is a directory with requester tracking."""

        return self._analysis.is_dir(
            requester=self._bound_requester(requester),
            path=self._absolute(path=path, legacy=requester is not None),
        )

    def is_file(
        self,
        *,
        path: ProjectPath | str | Path,
        requester: Path | None = None,
    ) -> bool:
        """Return whether a path is a file with requester tracking."""

        return self._analysis.is_file(
            requester=self._bound_requester(requester),
            path=self._absolute(path=path, legacy=requester is not None),
        )

    def glob(
        self,
        *,
        path: ProjectPath | str | Path,
        pattern: str,
        recursive: bool = False,
        requester: Path | None = None,
    ) -> tuple[Path, ...]:
        """Preserve the requester-aware legacy filesystem glob query."""

        return self._analysis.glob(
            requester=self._bound_requester(requester),
            path=self._absolute(path=path, legacy=requester is not None),
            pattern=pattern,
            recursive=recursive,
        )

    def dependencies(self) -> tuple[Any, ...]:
        """Return all dependencies observed by the shared project analysis."""

        return self._analysis.dependencies()

    def dependencies_for(self, *, requester: Path | None = None) -> tuple[Any, ...]:
        """Return dependencies for the bound or explicitly supplied legacy requester."""

        return self._analysis.dependencies_for(requester=self._bound_requester(requester))

    def absolute_path(self, path: ProjectPath | str) -> Path:
        """Resolve a confined public path for context-owned fault construction."""

        return self._absolute(path=path, legacy=False)

    def _bound_requester(self, requester: Path | None) -> Path:
        return self._requester if requester is None else requester

    def _absolute(self, *, path: ProjectPath | str | Path, legacy: bool) -> Path:
        if isinstance(path, Path):
            if legacy:
                return path
            from fensu.evaluation.exceptions import ProjectQueryTypeError

            raise ProjectQueryTypeError(
                "typed project queries accept only ProjectPath or str values"
            )
        relative: ProjectPath = path if isinstance(path, ProjectPath) else ProjectPath(path)
        return self._root.joinpath(*relative.parts)
