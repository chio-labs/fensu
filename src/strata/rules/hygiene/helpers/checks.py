"""Rule check functions for the hygiene family."""

from __future__ import annotations

import ast

from strata.discovery.core.types import ScopeName
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext

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


def single_line_docstrings(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag docstrings spanning more than one line."""

    del module
    return [
        ctx.fault_at(location) for location in ctx._analysis.facts.hygiene().multiline_docstrings
    ]


def no_standalone_comments(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag comments outside narrow tooling-directive exceptions."""

    del module
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.comments():
        if fact.text.startswith(_comment_allowed_prefixes):
            continue
        faults.append(ctx.fault_for(path=fact.path, line=fact.line, column=fact.column))
    return faults


def no_raw_builtin_raise(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag raises of generic built-in exception classes."""

    del module
    return [ctx.fault_at(location) for location in ctx._analysis.facts.hygiene().raw_builtin_raises]


def no_assert_in_runtime(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag assert statements in runtime code."""

    del module
    return [ctx.fault_at(location) for location in ctx._analysis.facts.hygiene().assertions]


def no_swallowed_exception_probe(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag broad exception handlers that silently answer existence probes."""

    del module
    return [
        ctx.fault_at(location)
        for location in ctx._analysis.facts.hygiene().swallowed_exception_probes
    ]


def no_complex_comprehensions_in_tooling(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Apply the global comprehension boundary to configured tooling."""

    del module
    if ctx.scope() is not ScopeName.TOOLING:
        return []
    return [ctx.fault_at(location) for location in ctx._analysis.facts.complex_comprehensions()]


def no_unnamed_string_decisions(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag string literals used directly as comparison values."""

    del module
    return [
        ctx.fault_at(location)
        for location in ctx._analysis.facts.hygiene().unnamed_string_decisions
    ]


def no_magic_numeric_comparisons(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag non-canonical numeric literals used directly as comparison values."""

    del module
    return [
        ctx.fault_at(location)
        for location in ctx._analysis.facts.hygiene().magic_numeric_comparisons
    ]
