"""Evaluation runtime protocols."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Protocol

from fensu.analysis.types import ProjectAnalysis
from fensu.discovery.models import ScopedFile
from fensu.evaluation.models import ParsedModule
from fensu.rules.authoring.models import ArchitectureGraph, Fault, ProjectTree

type NativeFaultRow = tuple[str, str | None, int | None, int | None, str | None, str | None]
type NativeFaultsByCode = dict[str, tuple[Fault, ...]]
type NativeThresholdValues = dict[str, int]
type NativeRuleOptionValues = dict[str, dict[str, str]]
type RepositoryEvaluation = tuple[
    list[dict[str, object]],
    list[dict[str, str]],
    tuple[str, ...],
    tuple[str, ...],
    bool,
    int,
    dict[str, int],
]
type NativeExecutionRequest = tuple[
    str,
    list[str],
    str,
    str | None,
    bool,
    NativeThresholdValues,
    str,
    list[tuple[str, str]],
    list[str],
    bool,
    str,
    tuple[
        list[str],
        list[tuple[str, str]],
        dict[str, list[str]],
        list[tuple[str, str, str, str, int, int]],
        str,
        NativeRuleOptionValues,
        list[str],
        int | None,
        str | None,
        list[str],
    ],
]
type NativeProjectFile = tuple[str, str, list[str], str, int | None, str | None]


class NativeProjectQueryKind(StrEnum):
    """Project observations requested by native FILE rules."""

    EXISTS = "exists"
    IS_FILE = "is_file"
    IS_DIR = "is_dir"
    DATACLASSES = "dataclasses"
    MODULE_FUNCTION = "module_function"
    PACKAGE_ANCHOR = "package_anchor"
    CUSTOM_RULE_COVERAGE = "custom_rule_coverage"
    DIRECTORY_ENTRIES = "directory_entries"
    GLOB = "glob"
    PYTHON_ANCHOR = "python_anchor"
    PUBLIC_FACADE = "public_facade"


class RepositoryDependencyKind(StrEnum):
    """Replayable target-qualified repository-rule observation kinds."""

    TREE_PATHS = "tree_paths"
    TREE_FILES = "tree_files"
    TREE_CHILDREN = "tree_children"
    TREE_DESCENDANTS = "tree_descendants"
    TREE_GLOB = "tree_glob"
    TREE_FILES_UNDER = "tree_files_under"
    TREE_POSITION = "tree_position"
    GRAPH_NODES = "graph_nodes"
    GRAPH_NODE = "graph_node"
    GRAPH_IMPORTS = "graph_imports"
    GRAPH_DEPENDENCIES = "graph_dependencies"
    GRAPH_DEPENDENTS = "graph_dependents"
    GRAPH_CYCLES = "graph_cycles"
    PYTHON_FILES = "python_files"
    PYTHON_FILE = "python_file"
    RUST_CRATES = "rust_crates"
    RUST_FILES = "rust_files"
    RUST_CRATE = "rust_crate"
    RUST_FILE = "rust_file"
    WEB_FILES = "web_files"
    WEB_FILE = "web_file"


class EvaluationProjectAnalysis(ProjectAnalysis, Protocol):
    """Project analysis with strict discovered-file parsing for evaluation."""

    def entrypoint_symbols(self, *, requester: Path) -> tuple[tuple[str, str], ...]:
        """Return full project script/plugin references with dependency evidence."""
        ...

    def parsed_module(self, scoped_file: ScopedFile) -> ParsedModule:
        """Return one strict discovered-file parse."""
        ...

    def prewarm(self, *, parsed: ParsedModule) -> None:
        """Adopt one pre-parsed discovered module for later single-use retrieval."""
        ...

    def native_source(self, *, requester: Path, path: Path) -> str | None:
        """Return decoded source while recording its source dependency without a CPython AST."""
        ...

    def architecture_graph(self, *, requester: Path) -> ArchitectureGraph:
        """Return the lazy graph with observations bound to one requester."""
        ...

    def graph_snapshot(self) -> dict[str, object]:
        """Return deterministic repository-relative graph replay facts."""
        ...

    @property
    def project_tree(self) -> ProjectTree:
        """Return immutable authoritative discovered-tree facts."""
        ...
