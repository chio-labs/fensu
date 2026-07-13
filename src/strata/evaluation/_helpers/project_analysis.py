"""Evaluation-scoped project analysis and dependency queries."""

from __future__ import annotations

from pathlib import Path

from strata.analysis.classes.query_observer import QueryObserver
from strata.analysis.exceptions import PythonSourceParseError
from strata.analysis.main.build import build_analysis
from strata.analysis.main.parse_source import parse_python_source
from strata.analysis.models import (
    DataclassFact,
    ProjectDependency,
    ProjectFunctionFact,
)
from strata.analysis.types import (
    Analysis,
    AnalysisBuild,
    ProjectDependencyKind,
    PythonSourceArtifact,
)
from strata.discovery.models import DiscoveredTree, ProjectSource, ScopedFile
from strata.evaluation._helpers.parsing import parse_scoped_file, read_source_snapshot
from strata.evaluation.exceptions import ParseError
from strata.evaluation.models import ExternalAnalysisBuild, ParsedModule, SourceSnapshot
from strata.evaluation.types import EvaluationProjectAnalysis

_test_types_file_name: str = "_test_types.py"


class _EvaluationProjectAnalysis:
    """Share parsed files and record cross-file inputs for one evaluation."""

    def __init__(self, *, tree: DiscoveredTree) -> None:
        """Index discovered files without parsing them eagerly."""

        self._repo_root: Path = tree.repo_root.path
        self._observer: QueryObserver = QueryObserver()
        self._sources: tuple[ProjectSource, ...] = (
            *tree.layout.runtime_sources,
            *tree.layout.tooling_sources,
            *(
                ProjectSource(
                    path=root.path,
                    relative_parts=root.relative_parts,
                    import_root=root.path.parent,
                    package_name=root.path.name,
                )
                for root in tree.layout.test_roots
            ),
        )
        self._scoped_files: dict[Path, ScopedFile] = {
            scoped_file.path.resolve(): scoped_file for scoped_file in tree.files
        }
        self._parsed_modules: dict[Path, ParsedModule] = {}
        self._external_analyses: dict[Path, Analysis] = {}
        self._queried_sources: set[Path] = set()
        self._source_answers: dict[Path, str | None] = {}
        self._dataclasses: dict[Path, tuple[DataclassFact, ...]] = {}
        self._dependencies: list[ProjectDependency] = []
        self._dependency_set: set[ProjectDependency] = set()
        self._resolved_paths: dict[Path, Path] = {}
        self._exists: dict[Path, bool] = {}
        self._directories: dict[Path, bool] = {}
        self._files: dict[Path, bool] = {}
        self._directory_entries: dict[Path, tuple[Path, ...]] = {}
        self._globs: dict[tuple[Path, str, bool], tuple[Path, ...]] = {}
        self._python_anchors: dict[Path, Path | None] = {}

    def parsed_module(self, scoped_file: ScopedFile) -> ParsedModule:
        """Return one strict discovered-file parse, reusing project queries."""

        path: Path = self._resolve(scoped_file.path)
        parsed: ParsedModule | None = self._parsed_modules.get(path)
        if parsed is None:
            parsed = parse_scoped_file(scoped_file=scoped_file)
        self._source_answers[path] = parsed.source_fingerprint
        if scoped_file.path.name == _test_types_file_name:
            self._dataclasses[path] = parsed.analysis.facts.dataclasses()
        self._parsed_modules.pop(path, None)
        self._queried_sources.discard(path)
        return parsed

    def analysis(self, *, requester: Path, path: Path) -> Analysis | None:
        """Return tolerant analysis for a queried path and record its dependency."""

        resolved_path: Path = self._resolve(path)
        parsed: ParsedModule | None = self._parsed_modules.get(resolved_path)
        external: Analysis | None = self._external_analyses.get(resolved_path)
        answer: str | None
        if resolved_path not in self._queried_sources:
            scoped_file: ScopedFile | None = self._scoped_files.get(resolved_path)
            if scoped_file is not None:
                parsed, answer = _build_discovered_analysis(scoped_file=scoped_file)
                if parsed is not None:
                    self._parsed_modules[resolved_path] = parsed
            else:
                external_build: ExternalAnalysisBuild = build_external_analysis(path=resolved_path)
                external = external_build.analysis
                answer = external_build.source_fingerprint
                if external is not None:
                    self._external_analyses[resolved_path] = external
            self._queried_sources.add(resolved_path)
            self._source_answers[resolved_path] = answer
        result: Analysis | None = parsed.analysis if parsed is not None else external
        self._record(
            requester=requester,
            dependency=path,
            kind=ProjectDependencyKind.SOURCE,
            answer=self._source_answers[resolved_path],
        )
        return result

    def dependencies(self) -> tuple[ProjectDependency, ...]:
        """Return deterministic requester-to-path dependencies observed so far."""

        return tuple(self._dependencies)

    def dependencies_for(self, *, requester: Path) -> tuple[ProjectDependency, ...]:
        """Return deterministic dependencies observed for one requester."""

        resolved_requester: Path = self._resolve(requester)
        return tuple(
            dependency
            for dependency in self._dependencies
            if dependency.requester == resolved_requester
        )

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
                answer=self._source_answers[resolved_path],
            )
        return self._dataclasses[resolved_path]

    def directory_entries(self, *, requester: Path, path: Path) -> tuple[Path, ...]:
        """Return direct children and record a directory namespace dependency."""

        query_path: Path = path.absolute()
        if query_path not in self._directory_entries:
            self._directory_entries[query_path] = self._observer.directory_entries(
                query_path=query_path
            )
        entries: tuple[Path, ...] = self._directory_entries[query_path]
        self._record(
            requester=requester,
            dependency=query_path,
            kind=ProjectDependencyKind.DIRECTORY_ENTRIES,
            answer=entries,
        )
        return entries

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
        if resolved_path not in self._exists:
            self._exists[resolved_path] = self._observer.exists(resolved_path=resolved_path)
        answer: bool = self._exists[resolved_path]
        self._record(
            requester=requester,
            dependency=path,
            kind=ProjectDependencyKind.EXISTS,
            answer=answer,
        )
        return answer

    def is_dir(self, *, requester: Path, path: Path) -> bool:
        """Return whether a path is a directory and record the dependency."""

        resolved_path: Path = self._resolve(path)
        if resolved_path not in self._directories:
            self._directories[resolved_path] = self._observer.is_dir(resolved_path=resolved_path)
        answer: bool = self._directories[resolved_path]
        self._record(
            requester=requester,
            dependency=path,
            kind=ProjectDependencyKind.IS_DIR,
            answer=answer,
        )
        return answer

    def is_file(self, *, requester: Path, path: Path) -> bool:
        """Return whether a path is a file and record the dependency."""

        resolved_path: Path = self._resolve(path)
        if resolved_path not in self._files:
            self._files[resolved_path] = self._observer.is_file(resolved_path=resolved_path)
        answer: bool = self._files[resolved_path]
        self._record(
            requester=requester,
            dependency=path,
            kind=ProjectDependencyKind.IS_FILE,
            answer=answer,
        )
        return answer

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
        if cache_key not in self._globs:
            self._globs[cache_key] = self._observer.glob(
                query_path=query_path,
                pattern=pattern,
                recursive=recursive,
            )
        matches: tuple[Path, ...] = self._globs[cache_key]
        self._record(
            requester=requester,
            dependency=query_path,
            kind=ProjectDependencyKind.GLOB,
            answer=matches,
            pattern=pattern,
            recursive=recursive,
        )
        return matches

    def python_anchor(self, *, requester: Path, path: Path) -> Path | None:
        """Return and record one compact deterministic Python ownership anchor."""

        query_path: Path = path.absolute()
        if query_path not in self._python_anchors:
            self._python_anchors[query_path] = self._observer.python_anchor(query_path=query_path)
        anchor: Path | None = self._python_anchors[query_path]
        answer: tuple[Path, ...] = () if anchor is None else (anchor,)
        self._record(
            requester=requester,
            dependency=query_path,
            kind=ProjectDependencyKind.PYTHON_ANCHOR,
            answer=answer,
        )
        return anchor

    def _module_path(self, *, requester: Path, module_name: str) -> Path | None:
        module_parts: tuple[str, ...] = tuple(module_name.split("."))
        if not module_parts:
            return None
        for source in self._sources:
            if source.package_name != module_parts[0]:
                continue
            if len(module_parts) == 1:
                package_path: Path = source.path / "__init__.py"
                if self.is_file(requester=requester, path=package_path):
                    return package_path
                continue
            relative_path: Path = Path(*module_parts[1:])
            module_path: Path = source.path / relative_path.with_suffix(".py")
            if self.is_file(requester=requester, path=module_path):
                return module_path
            package_path = source.path / relative_path / "__init__.py"
            if self.is_file(requester=requester, path=package_path):
                return package_path
        return None

    def _record(
        self,
        *,
        requester: Path,
        dependency: Path,
        kind: ProjectDependencyKind,
        answer: None | bool | str | tuple[Path, ...],
        pattern: str | None = None,
        recursive: bool = False,
    ) -> None:
        query_path: Path = dependency.absolute()
        observed: ProjectDependency = ProjectDependency(
            requester=self._resolve(requester),
            query_path=query_path,
            dependency=self._resolve(query_path),
            kind=kind,
            answer=answer,
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


def build_external_analysis(*, path: Path) -> ExternalAnalysisBuild:
    """Build tolerant analysis and source identity outside discovery."""

    try:
        snapshot: SourceSnapshot = read_source_snapshot(path=path)
    except OSError:
        return ExternalAnalysisBuild(analysis=None, source_fingerprint=None)
    try:
        artifact: PythonSourceArtifact = parse_python_source(
            path=path,
            content=snapshot.content,
            source_fingerprint=snapshot.fingerprint,
        )
    except PythonSourceParseError:
        return ExternalAnalysisBuild(analysis=None, source_fingerprint=snapshot.fingerprint)
    build: AnalysisBuild = build_analysis(
        path=artifact.path, source=artifact.source, module=artifact.module
    )
    return ExternalAnalysisBuild(
        analysis=build.analysis,
        source_fingerprint=artifact.source_fingerprint,
    )


def _build_discovered_analysis(
    *, scoped_file: ScopedFile
) -> tuple[ParsedModule | None, str | None]:
    try:
        snapshot: SourceSnapshot = read_source_snapshot(path=scoped_file.path)
    except OSError:
        return None, None
    try:
        parsed: ParsedModule = parse_scoped_file(scoped_file=scoped_file, source_snapshot=snapshot)
    except ParseError:
        return None, snapshot.fingerprint
    return parsed, parsed.source_fingerprint
