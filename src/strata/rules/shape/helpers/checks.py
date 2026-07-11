"""Rule check functions for the shape family."""

from __future__ import annotations

import ast

from strata.analysis.core.models import ProjectCallFacts, ProjectFunctionFact
from strata.discovery.core.types import RoleName
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext, Threshold


def too_many_statements(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag main/ top-level functions exceeding the tight statement threshold."""

    del module
    if not ctx.is_main_module():
        return []
    limit: int = ctx.threshold(Threshold.MAX_STATEMENTS)
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.functions().top_level:
        count: int = fact.statement_count
        if count > limit:
            faults.append(ctx.fault_at(fact.location, message=f"function has {count} statements"))
    return faults


def too_many_distinct_calls(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag main/ top-level functions with too many distinct callees."""

    del module
    if not ctx.is_main_module():
        return []
    limit: int = ctx.threshold(Threshold.MAX_DISTINCT_CALLS)
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.functions().top_level:
        count: int = fact.distinct_call_count
        if count > limit:
            faults.append(
                ctx.fault_at(fact.location, message=f"function calls {count} distinct functions")
            )
    return faults


def too_many_locals(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag main/ top-level functions juggling too many local variables."""

    del module
    if not ctx.is_main_module():
        return []
    limit: int = ctx.threshold(Threshold.MAX_LOCALS)
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.functions().top_level:
        count: int = fact.assigned_local_count
        if count > limit:
            faults.append(
                ctx.fault_at(fact.location, message=f"function defines {count} local variables")
            )
    return faults


def max_arguments(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag functions exceeding the configured argument limit."""

    del module
    limit: int = ctx.threshold(Threshold.MAX_ARGUMENTS)
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.functions().functions:
        count: int = fact.parameter_count
        if count > limit:
            faults.append(ctx.fault_at(fact.location, message=f"function has {count} parameters"))
    return faults


def max_statements_global(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag any function exceeding the loose global statement threshold."""

    del module
    limit: int = ctx.threshold(Threshold.MAX_STATEMENTS_GLOBAL)
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.functions().functions:
        count: int = fact.statement_count
        if count > limit:
            faults.append(ctx.fault_at(fact.location, message=f"function has {count} statements"))
    return faults


def meaningful_project_result_discarded(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag discarded meaningful results from resolved project-local calls."""

    del module
    if not ctx.is_main_module():
        return []
    facts: ProjectCallFacts = ctx._analysis.facts.project_calls()
    functions: tuple[ProjectFunctionFact, ...] = ctx._analysis.facts.project_functions()
    faults: list[Fault] = []
    for call in facts.discarded_calls:
        function: ProjectFunctionFact | None
        if call.module_name is None:
            function = next(
                (fact for fact in functions if fact.name == call.function_name),
                None,
            )
        else:
            function = ctx._project.module_function(
                requester=ctx.path,
                module_name=call.module_name,
                function_name=call.function_name,
            )
        if function is not None and function.meaningful_result:
            faults.append(ctx.fault_at(call.location))
    return faults


def parameter_mutation_in_phase_helpers(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag direct parameter mutation in helper functions."""

    if not ctx.in_role("helpers"):
        return []
    return _parameter_mutation_faults(module=module, ctx=ctx, require_return=False)


def default_mutation_return(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag parameter mutation unless all mutated parameters are returned."""

    return _parameter_mutation_faults(module=module, ctx=ctx, require_return=True)


def keyword_only_arguments(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag excess positional parameters that should be keyword-only."""

    del module
    limit: int = ctx.threshold(Threshold.MAX_POSITIONAL_ARGS)
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.functions().functions:
        if fact.dunder:
            continue
        count: int = fact.positional_parameter_count
        if count > limit:
            faults.append(
                ctx.fault_at(fact.location, message=f"function has {count} positional parameters")
            )
    return faults


def no_outer_state_mutation(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag function mutations of module-global or closure-captured state."""

    del module
    return [ctx.fault_at(fact.location) for fact in ctx._analysis.facts.outer_state_mutations()]


def no_complex_comprehensions(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag comprehensions that combine generators or nest another comprehension."""

    del module
    return [ctx.fault_at(location) for location in ctx._analysis.facts.complex_comprehensions()]


def mutable_result_model(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag dataclass result models that are not frozen."""

    del module
    if ctx.role_of() != RoleName.MODELS:
        return []
    return [
        ctx.fault_at(fact.location)
        for fact in ctx._analysis.facts.dataclasses()
        if fact.shape_candidate and not fact.frozen
    ]


def _parameter_mutation_faults(
    *, module: ast.Module, ctx: RuleContext, require_return: bool
) -> list[Fault]:
    del module
    return [
        ctx.fault_at(fact.location)
        for fact in ctx._analysis.facts.parameter_mutations()
        if not fact.dunder and not fact.setter and (not require_return or not fact.returned)
    ]
