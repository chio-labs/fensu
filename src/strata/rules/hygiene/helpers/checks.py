"""Rule check functions for the hygiene family."""

from __future__ import annotations

import ast
import io
import tokenize
from collections.abc import Iterator

from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext
from strata.rules.hygiene.types import HygieneCode

_comment_allowed_prefixes: tuple[str, ...] = (
    "#!",
    "# -*-",
    "# coding:",
    "# noqa",
    "# type:",
    "# pyright:",
    "# pylint:",
    "# pragma:",
)
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
_docstring_bearing_node_types: tuple[type[ast.AST], ...] = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
)


def single_line_docstrings(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag docstrings spanning more than one line."""

    faults: list[Fault] = []
    for node in _docstring_bearing_nodes(module):
        body: list[ast.stmt] | None = getattr(node, "body", None)
        if not body:
            continue
        first_statement: ast.stmt = body[0]
        if _statement_is_multiline_docstring(first_statement):
            faults.append(ctx.fault(first_statement))
    return faults


def no_standalone_comments(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag comments outside narrow tooling-directive exceptions."""

    del module
    faults: list[Fault] = []
    try:
        tokens: Iterator[tokenize.TokenInfo] = tokenize.generate_tokens(
            io.StringIO(ctx.source).readline
        )
        for token in tokens:
            if token.type != tokenize.COMMENT:
                continue
            comment: str = token.string.strip()
            if comment.startswith(_comment_allowed_prefixes):
                continue
            faults.append(
                Fault(
                    code=HygieneCode.NO_STANDALONE_COMMENTS,
                    path=ctx.path,
                    message="standalone comments are not allowed; prefer clear names or docs/tests",
                    line=token.start[0],
                    column=token.start[1],
                )
            )
    except tokenize.TokenError:
        return []
    return faults


def no_raw_builtin_raise(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag raises of generic built-in exception classes."""

    faults: list[Fault] = []
    for node in ctx.nodes(ast.Raise):
        if isinstance(node, ast.Raise) and _raise_uses_raw_builtin(node=node, ctx=ctx):
            faults.append(ctx.fault(node))
    return faults


def no_assert_in_runtime(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag assert statements in runtime code."""

    del module
    return [ctx.fault(node) for node in ctx.nodes(ast.Assert)]


def no_swallowed_exception_probe(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag broad exception handlers that silently answer existence probes."""

    del module
    faults: list[Fault] = []
    for node in ctx.nodes(ast.ExceptHandler):
        if (
            isinstance(node, ast.ExceptHandler)
            and _is_bare_exception_handler(node)
            and _handler_body_is_single_swallow(node.body)
        ):
            faults.append(ctx.fault(node))
    return faults


def _docstring_bearing_nodes(module: ast.Module) -> tuple[ast.AST, ...]:
    return (
        module,
        *(node for node in ast.walk(module) if isinstance(node, _docstring_bearing_node_types)),
    )


def _statement_is_multiline_docstring(node: ast.stmt) -> bool:
    if not isinstance(node, ast.Expr):
        return False
    if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
        return False
    end_lineno: int = getattr(node, "end_lineno", node.lineno)
    return end_lineno > node.lineno or "\n" in node.value.value


def _raise_uses_raw_builtin(*, node: ast.Raise, ctx: RuleContext) -> bool:
    if node.exc is None:
        return False
    raised_name: str | None = ctx.base_name(node.exc)
    return raised_name in _raw_builtin_raise_names


def _is_bare_exception_handler(node: ast.ExceptHandler) -> bool:
    return node.name is None and isinstance(node.type, ast.Name) and node.type.id == "Exception"


def _handler_body_is_single_swallow(body: list[ast.stmt]) -> bool:
    if len(body) != 1:
        return False
    statement: ast.stmt = body[0]
    if isinstance(statement, ast.Continue):
        return True
    if not isinstance(statement, ast.Return):
        return False
    return _is_swallowed_probe_return_value(statement.value)


def _is_swallowed_probe_return_value(node: ast.expr | None) -> bool:
    if isinstance(node, ast.Constant):
        return node.value is None or node.value is False
    if isinstance(node, ast.Dict):
        return not node.keys and not node.values
    if isinstance(node, ast.Tuple):
        return not node.elts
    return False
