"""Build dependency-recorded public graph facts from selected production sources."""

import sys
from pathlib import Path

import fensu._native as native
from fensu.analysis.models import (
    PythonEntryPointFact,
    PythonReachabilityFacts,
    PythonReferenceFact,
    PythonSymbolFact,
    PythonSymbolId,
    SourceLocation,
)
from fensu.analysis.types import PythonEntryPointKind, PythonSymbolKind
from fensu.config.main.configuration_directory import configuration_directory
from fensu.config.models import Config
from fensu.discovery.models import DiscoveredTree, ScopedFile
from fensu.discovery.types import ScopeName
from fensu.evaluation.constants import INIT_MODULE_NAME
from fensu.evaluation.exceptions import ParseError
from fensu.evaluation.main.select_files import select_evaluation_files
from fensu.evaluation.types import EvaluationProjectAnalysis


def build_reachability_facts(
    *, tree: DiscoveredTree, config: Config, analysis: EvaluationProjectAnalysis, requester: Path
) -> PythonReachabilityFacts:
    """Extract graph inputs without applying roots or calculating dead declarations."""

    sources: list[tuple[str, str, bool, bool]] = []
    paths: list[Path] = []
    for file in select_evaluation_files(
        tree=tree, config=config.evaluation, allow_empty=True
    ).files:
        if file.scope is ScopeName.TEST:
            continue
        source: str | None = analysis.native_source(requester=requester, path=file.path)
        if source is None:
            raise ParseError(
                path=file.path,
                message="Could not read reachability source.",
                line=None,
                column=None,
            )
        name, package, initializer = _module_identity(file=file)
        sources.append((name, source, package, initializer))
        paths.append(file.path)
    declarations, references, entries = native.python_reachability_facts(
        sources,
        list(analysis.entrypoint_symbols(requester=requester)),
        (sys.version_info.major, sys.version_info.minor),
    )
    project_root: Path = (
        tree.repo_root.path if tree.project_root is None else tree.project_root.path
    )
    directory: Path = configuration_directory(
        project_root=project_root, target_root=config.target_root
    )
    filename: str = "fensu.toml" if (directory / "fensu.toml").is_file() else "pyproject.toml"
    return PythonReachabilityFacts(
        symbols=tuple(
            _symbol_fact(index=index, row=row, paths=paths, sources=sources)
            for index, row in enumerate(declarations)
        ),
        references=tuple(
            PythonReferenceFact(PythonSymbolId(source), PythonSymbolId(target))
            for source, target in references
        ),
        entrypoints=tuple(
            PythonEntryPointFact(
                None if node is None else PythonSymbolId(node),
                PythonEntryPointKind(kind),
                reference,
            )
            for node, kind, reference in entries
        ),
        configuration_path=directory / filename,
    )


def _module_identity(*, file: ScopedFile) -> tuple[str, bool, bool]:
    parts: tuple[str, ...] = file.path.relative_to(file.root.parent).with_suffix("").parts
    initializer: bool = file.path.stem == INIT_MODULE_NAME
    parts = parts[:-1] if initializer else parts
    return ".".join(parts), initializer and len(parts) == 1, initializer


def _symbol_fact(
    *,
    index: int,
    row: tuple[int, str, str, int, int],
    paths: list[Path],
    sources: list[tuple[str, str, bool, bool]],
) -> PythonSymbolFact:
    module, name, kind, line, column = row
    return PythonSymbolFact(
        PythonSymbolId(index),
        sources[module][0],
        name,
        PythonSymbolKind(kind),
        SourceLocation(paths[module], line, column),
    )
