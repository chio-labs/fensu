"""Evaluation-scoped project analysis and dependency queries."""

from __future__ import annotations

import tomllib
from pathlib import Path

from fensu.analysis.classes.query_observer import QueryObserver
from fensu.analysis.exceptions import PythonSourceParseError
from fensu.analysis.main.build import build_analysis
from fensu.analysis.main.decode_source import decode_python_source
from fensu.analysis.main.parse_source import parse_python_source
from fensu.analysis.models import (
    DataclassFact,
    ProjectDependency,
    ProjectFunctionFact,
)
from fensu.analysis.types import (
    Analysis,
    ProjectDependencyKind,
    PythonSourceArtifact,
)
from fensu.discovery.models import DiscoveredTree, ProjectSource, ScopedFile
from fensu.evaluation._helpers.parsing import parse_scoped_file, read_source_snapshot
from fensu.evaluation.exceptions import ParseError
from fensu.evaluation.models import ExternalAnalysisBuild, ParsedModule, SourceSnapshot
from fensu.evaluation.types import EvaluationProjectAnalysis
from fensu.instrumentation.constants import (
    DEPENDENCY_RECORD_OPERATION,
    OPERATION_COUNTERS,
    PROJECT_QUERY_CACHE_HIT_OPERATION,
    PROJECT_QUERY_CACHE_MISS_OPERATION,
    PROJECT_QUERY_OBSERVATION_OPERATION,
    PROJECT_QUERY_SOURCE_OPERATION,
)

_test_types_file_name: str = "_test_types.py"
_pyproject_file_name: str = "pyproject.toml"


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
        self._scoped_files: dict[str, ScopedFile] = {
            str(scoped_file.path): scoped_file for scoped_file in tree.files
        }
        self._parsed_modules: dict[str, ParsedModule] = {}
        self._external_analyses: dict[str, Analysis] = {}
        self._queried_sources: set[str] = set()
        self._source_answers: dict[str, str | None] = {}
        self._dataclasses: dict[str, tuple[DataclassFact, ...]] = {}
        self._dependencies: list[ProjectDependency] = []
        self._dependencies_by_requester: dict[str, list[ProjectDependency]] = {}
        self._dependency_set: set[ProjectDependency] = set()
        self._recorded_queries: set[tuple[str, str, ProjectDependencyKind, str | None, bool]] = (
            set()
        )
        self._resolved_paths: dict[str, Path] = {
            str(scoped_file.path): scoped_file.path for scoped_file in tree.files
        }
        self._exists: dict[str, bool] = {}
        self._directories: dict[str, bool] = {}
        self._files: dict[str, bool] = {}
        self._directory_entries: dict[str, tuple[Path, ...]] = {}
        self._globs: dict[tuple[str, str, bool], tuple[Path, ...]] = {}
        self._python_anchors: dict[str, Path | None] = {}
        self._entrypoint_modules: tuple[str, ...] | None = None
        self._entrypoint_fingerprint: str | None = None

    def parsed_module(self, scoped_file: ScopedFile) -> ParsedModule:
        """Return one strict discovered-file parse, reusing project queries."""

        path: Path = self._resolve(scoped_file.path)
        path_key: str = str(path)
        parsed: ParsedModule | None = self._parsed_modules.get(path_key)
        if parsed is None:
            parsed = parse_scoped_file(scoped_file=scoped_file)
        self._source_answers[path_key] = parsed.source_fingerprint
        if scoped_file.path.name == _test_types_file_name:
            self._dataclasses[path_key] = parsed.analysis.facts.dataclasses()
        self._parsed_modules.pop(path_key, None)
        self._queried_sources.discard(path_key)
        return parsed

    def prewarm(self, *, parsed: ParsedModule) -> None:
        """Adopt one pre-parsed discovered module for later single-use retrieval."""

        path: Path = self._resolve(parsed.scoped_file.path)
        _ = self._parsed_modules.setdefault(str(path), parsed)
        if parsed.scoped_file.path.name == _test_types_file_name:
            self._source_answers[str(path)] = parsed.source_fingerprint
            self._dataclasses[str(path)] = parsed.analysis.facts.dataclasses()

    def analysis(self, *, requester: Path, path: Path) -> Analysis | None:
        """Return tolerant analysis for a queried path and record its dependency."""

        resolved_path: Path = self._resolve(path)
        path_key: str = str(resolved_path)
        parsed: ParsedModule | None = self._parsed_modules.get(path_key)
        external: Analysis | None = self._external_analyses.get(path_key)
        answer: str | None
        _record_query_cache(hit=path_key in self._queried_sources)
        if path_key not in self._queried_sources:
            OPERATION_COUNTERS.record(operation=PROJECT_QUERY_OBSERVATION_OPERATION)
            OPERATION_COUNTERS.record(operation=PROJECT_QUERY_SOURCE_OPERATION)
            scoped_file: ScopedFile | None = self._scoped_files.get(path_key)
            if scoped_file is not None:
                if parsed is None:
                    parsed, answer = _build_discovered_analysis(scoped_file=scoped_file)
                    if parsed is not None:
                        self._parsed_modules[path_key] = parsed
                else:
                    answer = parsed.source_fingerprint
            else:
                external_build: ExternalAnalysisBuild = build_external_analysis(path=resolved_path)
                external = external_build.analysis
                answer = external_build.source_fingerprint
                if external is not None:
                    self._external_analyses[path_key] = external
            self._queried_sources.add(path_key)
            self._source_answers[path_key] = answer
        result: Analysis | None = parsed.analysis if parsed is not None else external
        self._record(
            requester=requester,
            dependency=path,
            kind=ProjectDependencyKind.SOURCE,
            answer=self._source_answers[path_key],
        )
        return result

    def native_source(self, *, requester: Path, path: Path) -> str | None:
        """Return decoded source and record a source dependency without constructing an AST."""

        resolved_path: Path = self._resolve(path)
        try:
            snapshot: SourceSnapshot = read_source_snapshot(path=resolved_path)
            source: str | None = decode_python_source(path=resolved_path, content=snapshot.content)
        except (OSError, PythonSourceParseError):
            fingerprint: str | None = None
            source = None
        else:
            fingerprint = snapshot.fingerprint
        self._source_answers[str(resolved_path)] = fingerprint
        self._record(
            requester=requester,
            dependency=path,
            kind=ProjectDependencyKind.SOURCE,
            answer=fingerprint,
        )
        return source

    def dependencies(self) -> tuple[ProjectDependency, ...]:
        """Return deterministic requester-to-path dependencies observed so far."""

        return tuple(self._dependencies)

    def dependencies_for(self, *, requester: Path) -> tuple[ProjectDependency, ...]:
        """Return deterministic dependencies observed for one requester."""

        resolved_requester: Path = self._resolve(requester)
        return tuple(self._dependencies_by_requester.get(str(resolved_requester), ()))

    def dataclasses(self, *, requester: Path, path: Path) -> tuple[DataclassFact, ...]:
        """Return top-level dataclass facts for a project path."""

        resolved_path: Path = self._resolve(path)
        path_key: str = str(resolved_path)
        if path_key not in self._dataclasses:
            analysis: Analysis | None = self.analysis(requester=requester, path=path)
            if analysis is None:
                return ()
            self._dataclasses[path_key] = analysis.facts.dataclasses()
        else:
            self._record(
                requester=requester,
                dependency=path,
                kind=ProjectDependencyKind.SOURCE,
                answer=self._source_answers[path_key],
            )
        return self._dataclasses[path_key]

    def directory_entries(self, *, requester: Path, path: Path) -> tuple[Path, ...]:
        """Return direct children and record a directory namespace dependency."""

        query_path: Path = path.absolute()
        path_key: str = str(query_path)
        _record_query_cache(hit=path_key in self._directory_entries)
        if path_key not in self._directory_entries:
            self._directory_entries[path_key] = self._observer.directory_entries(
                query_path=query_path
            )
        entries: tuple[Path, ...] = self._directory_entries[path_key]
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

    def entrypoint_modules(self, *, requester: Path) -> tuple[str, ...]:
        """Return and record standardized modules referenced by project metadata."""

        path: Path = self._repo_root / _pyproject_file_name
        if self._entrypoint_modules is None:
            observed: tuple[str, str] | None = self._observer.source_text(path=path)
            if observed is None:
                self._entrypoint_modules = ()
            else:
                text, self._entrypoint_fingerprint = observed
                self._entrypoint_modules = _declared_entrypoint_modules(text=text)
        self._record(
            requester=requester,
            dependency=path,
            kind=ProjectDependencyKind.SOURCE,
            answer=self._entrypoint_fingerprint,
        )
        return self._entrypoint_modules

    def exists(self, *, requester: Path, path: Path) -> bool:
        """Return whether a path exists and record the dependency."""

        resolved_path: Path = self._resolve(path)
        path_key: str = str(resolved_path)
        _record_query_cache(hit=path_key in self._exists)
        if path_key not in self._exists:
            self._exists[path_key] = self._observer.exists(resolved_path=resolved_path)
        answer: bool = self._exists[path_key]
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
        path_key: str = str(resolved_path)
        _record_query_cache(hit=path_key in self._directories)
        if path_key not in self._directories:
            self._directories[path_key] = self._observer.is_dir(resolved_path=resolved_path)
        answer: bool = self._directories[path_key]
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
        path_key: str = str(resolved_path)
        _record_query_cache(hit=path_key in self._files)
        if path_key not in self._files:
            self._files[path_key] = self._observer.is_file(resolved_path=resolved_path)
        answer: bool = self._files[path_key]
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
        cache_key: tuple[str, str, bool] = (str(query_path), pattern, recursive)
        _record_query_cache(hit=cache_key in self._globs)
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
        path_key: str = str(query_path)
        _record_query_cache(hit=path_key in self._python_anchors)
        if path_key not in self._python_anchors:
            self._python_anchors[path_key] = self._observer.python_anchor(query_path=query_path)
        anchor: Path | None = self._python_anchors[path_key]
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
        query_key: tuple[str, str, ProjectDependencyKind, str | None, bool] = (
            str(requester),
            str(dependency),
            kind,
            pattern,
            recursive,
        )
        if query_key in self._recorded_queries:
            return
        self._recorded_queries.add(query_key)
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
            self._dependencies_by_requester.setdefault(str(observed.requester), []).append(observed)
            OPERATION_COUNTERS.record(operation=DEPENDENCY_RECORD_OPERATION)

    def _resolve(self, path: Path) -> Path:
        path_key: str = str(path)
        resolved: Path | None = self._resolved_paths.get(path_key)
        if resolved is None:
            resolved = path.resolve()
            self._resolved_paths[path_key] = resolved
        return resolved


def build_project_analysis(*, tree: DiscoveredTree) -> EvaluationProjectAnalysis:
    """Build one evaluation-scoped project analysis."""

    return _EvaluationProjectAnalysis(tree=tree)


def _record_query_cache(*, hit: bool) -> None:
    operation: str = (
        PROJECT_QUERY_CACHE_HIT_OPERATION if hit else PROJECT_QUERY_CACHE_MISS_OPERATION
    )
    OPERATION_COUNTERS.record(operation=operation)


def _declared_entrypoint_modules(*, text: str) -> tuple[str, ...]:
    try:
        document: dict[str, object] = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return ()
    project: object = document.get("project")
    if not isinstance(project, dict):
        return ()
    values: list[str] = []
    for section_name in ("scripts", "gui-scripts", "entry-points"):
        values.extend(_string_values(project.get(section_name)))
    modules: set[str] = set()
    for value in values:
        module_name: str = value.partition(":")[0].strip()
        if module_name:
            modules.add(module_name)
    return tuple(sorted(modules))


def _string_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, dict):
        return ()
    values: list[str] = []
    for nested in value.values():
        values.extend(_string_values(nested))
    return tuple(values)


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
    analysis: Analysis = build_analysis(
        path=artifact.path, source=artifact.source, module=artifact.module
    )
    return ExternalAnalysisBuild(
        analysis=analysis,
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
