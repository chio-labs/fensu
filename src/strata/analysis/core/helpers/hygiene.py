"""Syntax-based hygiene fact extraction."""

from __future__ import annotations

import ast
import io
import tokenize
from collections.abc import Mapping
from pathlib import Path

from strata.analysis.core.helpers.locations import source_location
from strata.analysis.core.models import CommentFact, HygieneFacts, SourceLocation

_raw_builtin_raise_names: frozenset[str] = frozenset(
    {
        "AssertionError",
        "Exception",
        "KeyError",
        "NotImplementedError",
        "RuntimeError",
        "TypeError",
        "ValueError",
    }
)
_exception_class_name: str = "Exception"
_frozenset_function_name: str = "frozenset"
_module_name_variable: str = "__name__"
_main_module_name: str = "__main__"
_newline_character: str = "\n"
_comment_marker: str = "#"


def comment_facts(*, path: Path, source: str) -> tuple[CommentFact, ...]:
    """Return source comments in token order, or no facts for incomplete tokens."""

    if _comment_marker not in source:
        return ()
    comments: list[CommentFact] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                comments.append(
                    CommentFact(
                        path=path,
                        line=token.start[0],
                        column=token.start[1],
                        text=token.string.strip(),
                    )
                )
    except tokenize.TokenError:
        return ()
    return tuple(comments)


def hygiene_facts(
    *,
    path: Path,
    module: ast.Module,
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
) -> HygieneFacts:
    """Return syntax-based hygiene facts from shared indexes."""

    return HygieneFacts(
        multiline_docstrings=_multiline_docstrings(path=path, module=module, node_index=node_index),
        raw_builtin_raises=tuple(
            source_location(path=path, node=node)
            for node in node_index.get(ast.Raise, ())
            if isinstance(node, ast.Raise) and _raise_uses_raw_builtin(node)
        ),
        assertions=tuple(
            source_location(path=path, node=node) for node in node_index.get(ast.Assert, ())
        ),
        swallowed_exception_probes=tuple(
            source_location(path=path, node=node)
            for node in node_index.get(ast.ExceptHandler, ())
            if isinstance(node, ast.ExceptHandler)
            and _is_bare_exception_handler(node)
            and _handler_body_is_single_swallow(node.body)
        ),
        unnamed_string_decisions=_decision_locations(
            path=path,
            nodes=node_index.get(ast.Compare, ()),
            strings=True,
        ),
        magic_numeric_comparisons=_decision_locations(
            path=path,
            nodes=node_index.get(ast.Compare, ()),
            strings=False,
        ),
    )


def _multiline_docstrings(
    *,
    path: Path,
    module: ast.Module,
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
) -> tuple[SourceLocation, ...]:
    locations: list[SourceLocation] = []
    nodes: tuple[ast.AST, ...] = (
        module,
        *node_index.get(ast.FunctionDef, ()),
        *node_index.get(ast.AsyncFunctionDef, ()),
        *node_index.get(ast.ClassDef, ()),
    )
    for node in nodes:
        body: list[ast.stmt] | None = getattr(node, "body", None)
        if body and _statement_is_multiline_docstring(body[0]):
            locations.append(source_location(path=path, node=body[0]))
    return tuple(locations)


def _statement_is_multiline_docstring(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
        and (
            getattr(node, "end_lineno", node.lineno) > node.lineno
            or _newline_character in node.value.value
        )
    )


def _raise_uses_raw_builtin(node: ast.Raise) -> bool:
    return node.exc is not None and _base_name(node.exc) in _raw_builtin_raise_names


def _base_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _base_name(node.value)
    if isinstance(node, ast.Call):
        return _base_name(node.func)
    return None


def _is_bare_exception_handler(node: ast.ExceptHandler) -> bool:
    return (
        node.name is None
        and isinstance(node.type, ast.Name)
        and node.type.id == _exception_class_name
    )


def _handler_body_is_single_swallow(body: list[ast.stmt]) -> bool:
    if len(body) != 1:
        return False
    statement: ast.stmt = body[0]
    if isinstance(statement, ast.Continue):
        return True
    return isinstance(statement, ast.Return) and _is_swallowed_probe_return_value(statement.value)


def _is_swallowed_probe_return_value(node: ast.expr | None) -> bool:
    if isinstance(node, ast.Constant):
        return node.value is None or node.value is False
    if isinstance(node, ast.Dict):
        return not node.keys and not node.values
    if isinstance(node, ast.Tuple):
        return not node.elts
    return False


def _decision_locations(
    *, path: Path, nodes: tuple[ast.AST, ...], strings: bool
) -> tuple[SourceLocation, ...]:
    locations: list[SourceLocation] = []
    for node in nodes:
        if not isinstance(node, ast.Compare) or (strings and _is_main_execution_guard(node)):
            continue
        for operand in (node.left, *node.comparators):
            for literal in _decision_literal_nodes(operand):
                if strings and isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                    locations.append(source_location(path=path, node=literal))
                if not strings:
                    value: object = _numeric_literal_value(literal)
                    if value is not None and value not in {-1, 0, 1}:
                        locations.append(source_location(path=path, node=literal))
    return tuple(locations)


def _decision_literal_nodes(node: ast.expr) -> tuple[ast.expr, ...]:
    if isinstance(node, ast.Constant | ast.UnaryOp):
        return (node,)
    if isinstance(node, ast.List | ast.Set | ast.Tuple):
        literals: list[ast.expr] = []
        for element in node.elts:
            literals.extend(_decision_literal_nodes(element))
        return tuple(literals)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == _frozenset_function_name
        and len(node.args) == 1
    ):
        return _decision_literal_nodes(node.args[0])
    return ()


def _numeric_literal_value(node: ast.expr) -> int | float | complex | None:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float | complex):
            return None
        return node.value
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and not isinstance(node.operand.value, bool)
        and isinstance(node.operand.value, int | float | complex)
    ):
        return -node.operand.value
    return None


def _is_main_execution_guard(node: ast.Compare) -> bool:
    return (
        len(node.ops) == 1
        and isinstance(node.ops[0], ast.Eq)
        and len(node.comparators) == 1
        and isinstance(node.left, ast.Name)
        and node.left.id == _module_name_variable
        and isinstance(node.comparators[0], ast.Constant)
        and node.comparators[0].value == _main_module_name
    )
