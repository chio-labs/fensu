"""Evaluation-scoped project analysis and dependency queries."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.analysis.core.main.build import build_analysis
from strata.analysis.core.models import DataclassFact, ProjectDependency, ProjectFunctionFact
from strata.analysis.core.types import Analysis, AnalysisBuild, ProjectDependencyKind
from strata.discovery.core.models import DiscoveredTree, ScopedFile
from strata.evaluation.core.exceptions import ParseError
from strata.evaluation.core.helpers.parsing import parse_scoped_file
from strata.evaluation.core.models import ParsedModule
from strata.evaluation.core.types import EvaluationProjectAnalysis

_test_types_file_name: str = "_test_types.py"


class _EvaluationProjectAnalysis:
    """Share parsed files and record cross-file inputs for one evaluation."""

    def __init__(self, *, tree: DiscoveredTree) -> None:
        """Index discovered files without parsing them eagerly."""

        self._repo_root: Path = tree.repo_root.path
        self._scoped_files: dict[Path, ScopedFile] = {
            scoped_file.path.resolve(): scoped_file for scoped_file in tree.files
        }
        self._parsed_modules: dict[Path, ParsedModule] = {}
        self._external_analyses: dict[Path, Analysis] = {}
        self._dataclasses: dict[Path, tuple[DataclassFact, ...]] = {}
        self._dependencies: list[ProjectDependency] = []
        self._dependency_set: set[ProjectDependency] = set()
        self._resolved_paths: dict[Path, Path] = {}
        self._exists: dict[Path, bool] = {}
        self._directories: dict[Path, bool] = {}
        self._files: dict[Path, bool] = {}
        self._directory_entries: dict[Path, tuple[Path, ...]] = {}
        self._globs: dict[tuple[Path, str, bool], tuple[Path, ...]] = {}

    def parsed_module(self, scoped_file: ScopedFile) -> ParsedModule:
        """Return one strict discovered-file parse, reusing project queries."""

        path: Path = self._resolve(scoped_file.path)
        parsed: ParsedModule | None = self._parsed_modules.get(path)
        if parsed is None:
            parsed = parse_scoped_file(scoped_file)
        if scoped_file.path.name == _test_types_file_name:
            self._dataclasses[path] = parsed.analysis.facts.dataclasses()
        self._parsed_modules.pop(path, None)
        return parsed

    def analysis(self, *, requester: Path, path: Path) -> Analysis | None:
        """Return tolerant analysis for a queried path and record its dependency."""

        resolved_path: Path = self._resolve(path)
        self._record(
            requester=requester,
            dependency=path,
            kind=ProjectDependencyKind.SOURCE,
        )
        parsed: ParsedModule | None = self._parsed_modules.get(resolved_path)
        if parsed is not None:
            return parsed.analysis
        external: Analysis | None = self._external_analyses.get(resolved_path)
        if external is not None:
            return external
        scoped_file: ScopedFile | None = self._scoped_files.get(resolved_path)
        if scoped_file is not None:
            try:
                parsed = parse_scoped_file(scoped_file)
            except (OSError, ParseError, UnicodeError):
                return None
            self._parsed_modules[resolved_path] = parsed
            return parsed.analysis
        external = build_external_analysis(path=resolved_path)
        if external is None:
            return None
        self._external_analyses[resolved_path] = external
        return external

    def dependencies(self) -> tuple[ProjectDependency, ...]:
        """Return deterministic requester-to-path dependencies observed so far."""

        return tuple(self._dependencies)

    def dataclasses(self, *, requester: Path, path: Path) -> tuple[DataclassFact, ...]:
        """Return top-level dataclass facts for a project path."""

        resolved_path: Path = self._resolve(path)
        if resolved_path not in self._dataclasses:
            analysis: Analysis | None = self.analysis(requester=requester, path=path)
            if analysis is None:
                return ()
            self._dataclasses[resolved_path] = analysis.facts.dataclasses()
        else:
            self._record(
                requester=requester,
                dependency=path,
                kind=ProjectDependencyKind.SOURCE,
            )
        return self._dataclasses[resolved_path]

    def directory_entries(self, *, requester: Path, path: Path) -> tuple[Path, ...]:
        """Return direct children and record a directory namespace dependency."""

        query_path: Path = path.absolute()
        self._record(
            requester=requester,
            dependency=query_path,
            kind=ProjectDependencyKind.DIRECTORY_ENTRIES,
        )
        if query_path not in self._directory_entries:
            self._directory_entries[query_path] = tuple(query_path.iterdir())
        return self._directory_entries[query_path]

    def module_function(
        self, *, requester: Path, module_name: str, function_name: str
    ) -> ProjectFunctionFact | None:
        """Return the first matching function contract from a project module."""

        module_path: Path | None = self._module_path(
            requester=requester,
            module_name=module_name,
        )
        if module_path is None:
            return None
        analysis: Analysis | None = self.analysis(requester=requester, path=module_path)
        if analysis is None:
            return None
        return next(
            (fact for fact in analysis.facts.project_functions() if fact.name == function_name),
            None,
        )

    def exists(self, *, requester: Path, path: Path) -> bool:
        """Return whether a path exists and record the dependency."""

        resolved_path: Path = self._resolve(path)
        self._record(
            requester=requester,
            dependency=path,
            kind=ProjectDependencyKind.EXISTS,
        )
        if resolved_path not in self._exists:
            self._exists[resolved_path] = resolved_path.exists()
        return self._exists[resolved_path]

    def is_dir(self, *, requester: Path, path: Path) -> bool:
        """Return whether a path is a directory and record the dependency."""

        resolved_path: Path = self._resolve(path)
        self._record(
            requester=requester,
            dependency=path,
            kind=ProjectDependencyKind.IS_DIR,
        )
        if resolved_path not in self._directories:
            self._directories[resolved_path] = resolved_path.is_dir()
        return self._directories[resolved_path]

    def is_file(self, *, requester: Path, path: Path) -> bool:
        """Return whether a path is a file and record the dependency."""

        resolved_path: Path = self._resolve(path)
        self._record(
            requester=requester,
            dependency=path,
            kind=ProjectDependencyKind.IS_FILE,
        )
        if resolved_path not in self._files:
            self._files[resolved_path] = resolved_path.is_file()
        return self._files[resolved_path]

    def glob(
        self,
        *,
        requester: Path,
        path: Path,
        pattern: str,
        recursive: bool = False,
    ) -> tuple[Path, ...]:
        """Return direct or recursive path matches and record an aggregate dependency."""

        query_path: Path = path.absolute()
        cache_key: tuple[Path, str, bool] = (query_path, pattern, recursive)
        self._record(
            requester=requester,
            dependency=query_path,
            kind=ProjectDependencyKind.GLOB,
            pattern=pattern,
            recursive=recursive,
        )
        if cache_key not in self._globs:
            self._globs[cache_key] = tuple(
                query_path.rglob(pattern) if recursive else query_path.glob(pattern)
            )
        return self._globs[cache_key]

    def _module_path(self, *, requester: Path, module_name: str) -> Path | None:
        relative_path: Path = Path(*module_name.split("."))
        for source_root in (self._repo_root / "src", self._repo_root):
            module_path: Path = source_root / relative_path.with_suffix(".py")
            if self.is_file(requester=requester, path=module_path):
                return module_path
            package_path: Path = source_root / relative_path / "__init__.py"
            if self.is_file(requester=requester, path=package_path):
                return package_path
        return None

    def _record(
        self,
        *,
        requester: Path,
        dependency: Path,
        kind: ProjectDependencyKind,
        pattern: str | None = None,
        recursive: bool = False,
    ) -> None:
        query_path: Path = dependency.absolute()
        observed: ProjectDependency = ProjectDependency(
            requester=self._resolve(requester),
            query_path=query_path,
            dependency=self._resolve(query_path),
            kind=kind,
            pattern=pattern,
            recursive=recursive,
        )
        if observed not in self._dependency_set:
            self._dependency_set.add(observed)
            self._dependencies.append(observed)

    def _resolve(self, path: Path) -> Path:
        resolved: Path | None = self._resolved_paths.get(path)
        if resolved is None:
            resolved = path.resolve()
            self._resolved_paths[path] = resolved
        return resolved


def build_project_analysis(*, tree: DiscoveredTree) -> EvaluationProjectAnalysis:
    """Build one evaluation-scoped project analysis."""

    return _EvaluationProjectAnalysis(tree=tree)


def build_external_analysis(*, path: Path) -> Analysis | None:
    """Build tolerant analysis for a Python file outside discovery."""

    try:
        source: str = path.read_text(encoding="utf-8")
        module: ast.Module = ast.parse(source)
    except (OSError, SyntaxError, UnicodeError):
        return None
    analysis_build: AnalysisBuild = build_analysis(path=path, source=source, module=module)
    return analysis_build.analysis
