"""Evaluation runtime models."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from strata.analysis.models import ProjectDependency
from strata.analysis.types import Analysis
from strata.discovery.models import PositionFacts, ScopedFile
from strata.rules.authoring.models import Fault


@dataclass(frozen=True, slots=True)
class ParsedModule:
    """A discovered Python file parsed into an AST plus shared traversal facts."""

    scoped_file: ScopedFile
    module: ast.Module
    source: str
    source_fingerprint: str
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]]
    parent_by_node: Mapping[ast.AST, ast.AST]
    position: PositionFacts
    analysis: Analysis


@dataclass(frozen=True, slots=True)
class RuleExceptionKey:
    """One exact configured rule, path, and qualified-symbol exception."""

    rule: str
    path: str
    symbol: str


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    """Exact source bytes and their stable content identity."""

    content: bytes
    fingerprint: str


@dataclass(frozen=True, slots=True)
class ExternalAnalysisBuild:
    """Tolerant external analysis plus the readable source identity."""

    analysis: Analysis | None
    source_fingerprint: str | None


@dataclass(frozen=True, slots=True)
class FileEvaluation:
    """Unrendered evaluation output and observed inputs for one source file."""

    path: Path
    source_fingerprint: str
    faults: tuple[Fault, ...]
    applied_exception_keys: tuple[RuleExceptionKey, ...]
    dependencies: tuple[ProjectDependency, ...]


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Evaluation output for a discovered tree."""

    faults: tuple[Fault, ...]
    applied_exception_count: int = 0
    dependencies: tuple[ProjectDependency, ...] = ()
    file_evaluations: tuple[FileEvaluation, ...] = ()
