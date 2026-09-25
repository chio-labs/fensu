"""Invoke native production reachability policy from the Python project-rule host."""

import fensu._native as native
from fensu.analysis.models import PythonReachabilityFacts, PythonSymbolFact
from fensu.analysis.types import PythonSymbolKind
from fensu.rules.authoring.models import Fault, Project
from fensu.rules.authoring.types import RuleContext
from fensu.rules.layers.types import LayerCode


def check_unreachable_definition(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Evaluate definition reachability through inspectable, module-free project facts."""

    return _check_dead_code(project=project, ctx=ctx, code=LayerCode.UNREACHABLE_DEFINITION)


def check_stale_dead_code_root(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Evaluate configured roots through inspectable, module-free project facts."""

    return _check_dead_code(project=project, ctx=ctx, code=LayerCode.STALE_DEAD_CODE_ROOT)


def check_unreachable_module(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Evaluate module execution through inspectable, module-free project facts."""

    return _check_dead_code(project=project, ctx=ctx, code=LayerCode.UNREACHABLE_MODULE)


def _check_dead_code(*, project: Project, ctx: RuleContext, code: LayerCode) -> list[Fault]:
    """Keep project diagnostics executable even with an empty selected source surface."""

    del project
    if not ctx.project.dead_code.enabled:
        return []
    facts: PythonReachabilityFacts = ctx.project.python_reachability()
    modules: list[str] = sorted({symbol.module for symbol in facts.symbols})
    module_indexes: dict[str, int] = {module: index for index, module in enumerate(modules)}
    dead, stale = native.evaluate_python_reachability(
        (
            modules,
            [
                (module_indexes[symbol.module], symbol.name, symbol.kind is PythonSymbolKind.LOCAL)
                for symbol in facts.symbols
            ],
            [(edge.source.value, edge.target.value) for edge in facts.references],
            [entry.symbol.value for entry in facts.entrypoints if entry.symbol is not None],
        ),
        [(list(root.modules), list(root.symbols)) for root in ctx.project.dead_code.roots],
    )
    if code == LayerCode.STALE_DEAD_CODE_ROOT:
        return [
            ctx.fault_for(
                path=facts.configuration_path,
                line=1,
                column=0,
                message=(
                    f"dead_code.roots entry {index + 1} matches no existing production declaration"
                ),
                remediation=(
                    "Remove or correct the stale configured root; "
                    "matching does not depend on current reachability."
                ),
            )
            for index in stale
        ]
    modules_only: bool = code == LayerCode.UNREACHABLE_MODULE
    return [
        _declaration_fault(ctx=ctx, symbol=facts.symbols[index])
        for index in dead
        if (facts.symbols[index].kind is PythonSymbolKind.MODULE) == modules_only
    ]


def _declaration_fault(*, ctx: RuleContext, symbol: PythonSymbolFact) -> Fault:
    qualified: str = symbol.module if not symbol.name else f"{symbol.module}.{symbol.name}"
    return ctx.fault_at(
        location=symbol.location,
        message=f"unreachable {symbol.kind.value} {qualified}",
        remediation=(
            "Investigate the production entry mechanism before deleting code. "
            "Export an intentional public API or configure a reasoned root for dynamic dispatch."
        ),
    )
