"""Shared helpers for rule authoring tests."""

from __future__ import annotations

import ast

from strata.rules.spec.models import Fault, RuleContext


def empty_check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """A no-op rule check body usable as a placeholder in tests."""

    return []
