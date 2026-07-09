"""Evaluation runtime models."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass

from strata.discovery.core.models import ScopedFile
from strata.rules.authoring.models import Fault


@dataclass(frozen=True, slots=True)
class ParsedModule:
    """A discovered Python file parsed into an AST plus shared traversal facts."""

    scoped_file: ScopedFile
    module: ast.Module
    source: str
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]]
    parent_by_node: Mapping[ast.AST, ast.AST]


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Evaluation output for a discovered tree."""

    faults: tuple[Fault, ...]
