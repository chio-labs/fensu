"""Custom rule declarations exercised by the public harness integration tests."""

from __future__ import annotations

import ast
from pathlib import Path

from strata import (
    Family,
    Fault,
    FunctionFacts,
    ProjectFunctionFact,
    RuleContext,
    SyntaxHandle,
    Threshold,
    rule,
)


@rule(
    code="XHT001",
    family=Family.CUSTOM,
    slug="all-context-zones",
    message="all public context zones are available",
)
def all_context_zones(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise facts, project, text, syntax, and relations through the real context."""

    function_facts: FunctionFacts = ctx.facts.functions()
    source_line: str = ctx.text.line(1)
    handles: tuple[SyntaxHandle, ...] = ctx.syntax.handles()
    parent: SyntaxHandle | None = ctx.relations.parent(handles[-1])
    support_function: ProjectFunctionFact | None = ctx.project.module_function(
        requester=ctx.path,
        module_name="example.support",
        function_name="support_value",
    )
    directory_entries: tuple[Path, ...] = ctx.project.directory_entries(
        requester=ctx.path,
        path=ctx.scope_root(),
    )
    del function_facts, source_line, parent, support_function, directory_entries
    return [ctx.fault(node=module.body[0])]


@rule(
    code="XHT002",
    family=Family.CUSTOM,
    slug="always-fault",
    message="one direct target",
)
def always_fault(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Emit one fault for every direct evaluation target."""

    return [ctx.fault(node=module.body[0])]


@rule(
    code="XHT003",
    family=Family.CUSTOM,
    slug="context-policy",
    message="context policy",
)
def context_policy(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Expose scope, role, thresholds, and contracts in one observable fault."""

    del module
    message: str = "|".join(
        (
            ctx.scope().value,
            ctx.role_of() or "none",
            str(ctx.threshold(name=Threshold.MAX_STATEMENTS)),
            ctx.contracts().get("inspect_*", "missing"),
            ctx.scope_root().relative_to(ctx.repo_root).as_posix(),
        )
    )
    return [ctx.path_fault(message=message)]


@rule(
    code="XHT004",
    family=Family.CUSTOM,
    slug="ordinary-ordering",
    message="ordinary ordering",
)
def ordinary_ordering(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Return reverse-source findings so the ordinary collector must order them."""

    return [ctx.fault(node=module.body[1]), ctx.fault(node=module.body[0])]


@rule(
    code="XNF001",
    family=Family.CUSTOM,
    slug="native-class-declarations",
    message="adapter class declaration",
)
def native_class_declarations(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise class declaration facts without reading the raw module."""

    del module
    return [ctx.fault_at(location=fact.location) for fact in ctx.facts.class_declarations()]


@rule(
    code="XNF002",
    family=Family.CUSTOM,
    slug="native-assignment-references",
    message="base adapter assignment reference",
)
def native_assignment_references(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise assignment reference facts without reading the raw module."""

    del module
    return [ctx.fault_at(location=fact.location) for fact in ctx.facts.assignment_references()]


@rule(
    code="XNF003",
    family=Family.CUSTOM,
    slug="native-named-calls",
    message="discarded metadata call in loop",
)
def native_named_calls(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise named call facts without reading the raw module."""

    del module
    return [ctx.fault_at(location=fact.location) for fact in ctx.facts.named_calls()]


@rule(
    code="XNF004",
    family=Family.CUSTOM,
    slug="native-local-call-edges",
    message="metadata query call edge in loop",
)
def native_local_call_edges(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise local call edges without reading the raw module."""

    del module
    return [ctx.fault_at(location=fact.location) for fact in ctx.facts.local_call_edges()]


@rule(
    code="XNF005",
    family=Family.CUSTOM,
    slug="native-comparisons",
    message="canonical reference comparison",
)
def native_comparisons(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise comparison facts without reading the raw module."""

    del module
    return [ctx.fault_at(location=fact.location) for fact in ctx.facts.comparisons()]


@rule(
    code="XNF006",
    family=Family.CUSTOM,
    slug="native-parameter-mutation-occurrences",
    message="parameter mutation occurrence",
)
def native_parameter_mutation_occurrences(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise complete parameter mutation facts without reading the raw module."""

    del module
    return [
        ctx.fault_at(location=fact.location) for fact in ctx.facts.parameter_mutation_occurrences()
    ]


def undecorated_rule(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Provide an invalid undecorated harness input."""

    del module, ctx
    return []
