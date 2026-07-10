"""Shared traversal for function and local annotation facts."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.analysis.core.helpers.locations import line_offsets, source_range
from strata.analysis.core.models import (
    AnnotationFacts,
    MissingLocalAnnotationFact,
    MissingParameterAnnotationFact,
    MissingReturnAnnotationFact,
    SourceRange,
)

_receiver_names: frozenset[str] = frozenset({"self", "cls"})
_enum_base_names: frozenset[str] = frozenset({"Enum", "StrEnum"})
_discard_name: str = "_"


class _AnnotationVisitor(ast.NodeVisitor):
    def __init__(self, *, path: Path, source: str) -> None:
        self._path: Path = path
        self._source: str = source
        self._line_offsets: tuple[int, ...] = line_offsets(source)
        self._parameters: list[MissingParameterAnnotationFact] = []
        self._returns: list[MissingReturnAnnotationFact] = []
        self._locals: list[MissingLocalAnnotationFact] = []
        self._class_depth: int = 0
        self._function_scopes: list[set[str]] = []

    def collect(self, module: ast.Module) -> AnnotationFacts:
        self.visit(module)
        return AnnotationFacts(
            parameters=tuple(self._parameters),
            returns=tuple(self._returns),
            locals=tuple(self._locals),
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_depth += 1
        is_enum_class: bool = _is_enum_class(node)
        try:
            for statement in node.body:
                if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                    self.visit(statement)
                    continue
                if isinstance(statement, ast.Assign | ast.AugAssign):
                    self.generic_visit(statement)
                    continue
                if isinstance(statement, ast.AnnAssign):
                    if (
                        not is_enum_class
                        and self._function_scopes
                        and isinstance(statement.target, ast.Name)
                    ):
                        self._function_scopes[-1].add(statement.target.id)
                    if is_enum_class:
                        self.generic_visit(statement)
                    continue
                self.visit(statement)
        finally:
            self._class_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._record_local_assignments(node)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._record_local_assignments(node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if self._function_scopes and isinstance(node.target, ast.Name):
            self._function_scopes[-1].add(node.target.id)
        self.generic_visit(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._record_function_annotations(node)
        self._function_scopes.append(_annotated_parameter_names(node))
        try:
            for statement in node.body:
                self.visit(statement)
        finally:
            self._function_scopes.pop()

    def _record_function_annotations(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        positional_args: list[ast.arg] = [*node.args.posonlyargs, *node.args.args]
        exempt_name: str | None = None
        if self._class_depth > 0 and positional_args and positional_args[0].arg in _receiver_names:
            exempt_name = positional_args[0].arg
        parameters: list[ast.arg | None] = [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
            node.args.vararg,
            node.args.kwarg,
        ]
        for parameter in parameters:
            if (
                parameter is None
                or parameter.annotation is not None
                or parameter.arg == exempt_name
            ):
                continue
            self._parameters.append(
                MissingParameterAnnotationFact(
                    name=parameter.arg,
                    location=self._location(parameter),
                )
            )
        if node.returns is None:
            self._returns.append(
                MissingReturnAnnotationFact(name=node.name, location=self._location(node))
            )

    def _record_local_assignments(self, node: ast.Assign | ast.AugAssign) -> None:
        if not self._function_scopes:
            return
        current_scope: set[str] = self._function_scopes[-1]
        targets: list[ast.expr] = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if (
                not isinstance(target, ast.Name)
                or target.id == _discard_name
                or target.id in current_scope
            ):
                continue
            self._locals.append(
                MissingLocalAnnotationFact(name=target.id, location=self._location(target))
            )
            current_scope.add(target.id)

    def _location(self, node: ast.AST) -> SourceRange:
        return source_range(
            path=self._path,
            source=self._source,
            line_offsets=self._line_offsets,
            node=node,
        )


def annotation_facts(*, path: Path, source: str, module: ast.Module) -> AnnotationFacts:
    """Return shared missing-annotation facts from one file traversal."""

    return _AnnotationVisitor(path=path, source=source).collect(module)


def _annotated_parameter_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    parameters: list[ast.arg | None] = [
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
        node.args.vararg,
        node.args.kwarg,
    ]
    for parameter in parameters:
        if parameter is not None and (
            parameter.annotation is not None or parameter.arg in _receiver_names
        ):
            names.add(parameter.arg)
    return names


def _is_enum_class(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in _enum_base_names:
            return True
        if isinstance(base, ast.Attribute) and base.attr in _enum_base_names:
            return True
    return False
