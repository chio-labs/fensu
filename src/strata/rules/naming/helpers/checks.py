"""Rule check functions for the naming family."""

from __future__ import annotations

import ast
from fnmatch import fnmatchcase

from strata.config.core.types import ContractBehavior
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext


def validator_must_not_return(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag meaningful returns from functions under no-return name contracts."""

    del module
    patterns: tuple[str, ...] = tuple(
        pattern
        for pattern, behavior in ctx.contracts().items()
        if behavior == ContractBehavior.NO_RETURN
    )
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.meaningful_returns():
        if any(fnmatchcase(fact.function_name, pattern) for pattern in patterns):
            faults.append(ctx.fault_at(fact.location))
    return faults
