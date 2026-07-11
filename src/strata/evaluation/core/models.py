"""Evaluation runtime models."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass

from strata.analysis.core.models import ProjectDependency
from strata.analysis.core.types import Analysis
from strata.discovery.core.models import PositionFacts, ScopedFile
from strata.rules.authoring.models import Fault


@dataclass(frozen=True, slots=True)
class ParsedModule:
    """A discovered Python file parsed into an AST plus shared traversal facts."""

    scoped_file: ScopedFile
    module: ast.Module
    source: str
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
class EvaluationResult:
    """Evaluation output for a discovered tree."""

    faults: tuple[Fault, ...]
    applied_exception_count: int = 0
    dependencies: tuple[ProjectDependency, ...] = ()
