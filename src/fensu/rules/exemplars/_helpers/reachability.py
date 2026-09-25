"""Independent reachability policy implemented exclusively with public graph facts."""

from fensu import (
    Fault,
    PythonReachabilityFacts,
    PythonSymbolId,
    PythonSymbolKind,
    RuleContext,
    matches_symbol_patterns,
)

_dead_remediation: str = (
    "Investigate the production entry mechanism before deleting code. "
    "Export an intentional public API or configure a reasoned root for dynamic dispatch."
)
_stale_remediation: str = (
    "Remove or correct the stale configured root; matching does not depend on current reachability."
)


def unreachable_symbols(*, ctx: RuleContext, modules_only: bool) -> list[Fault]:
    """Traverse public dependency edges rather than asking native code for its verdict."""

    if not ctx.project.dead_code.enabled:
        return []
    facts, live, _ = _graph_state(ctx=ctx)
    faults: list[Fault] = []
    for symbol in facts.symbols:
        if symbol.id in live or symbol.kind is PythonSymbolKind.LOCAL:
            continue
        if (symbol.kind is PythonSymbolKind.MODULE) != modules_only:
            continue
        qualified: str = symbol.module if not symbol.name else f"{symbol.module}.{symbol.name}"
        faults.append(
            ctx.fault_at(
                location=symbol.location,
                message=f"unreachable {symbol.kind.value} {qualified}",
                remediation=_dead_remediation,
            )
        )
    return faults


def stale_roots(*, ctx: RuleContext) -> list[Fault]:
    """Find patterns with no declaration matches, independently of current liveness."""

    if not ctx.project.dead_code.enabled:
        return []
    facts, _, stale = _graph_state(ctx=ctx)
    return [
        ctx.fault_for(
            path=facts.configuration_path,
            line=1,
            column=0,
            message=f"dead_code.roots entry {index + 1} matches no existing production declaration",
            remediation=_stale_remediation,
        )
        for index in stale
    ]


def _graph_state(
    *, ctx: RuleContext
) -> tuple[PythonReachabilityFacts, set[PythonSymbolId], list[int]]:
    facts: PythonReachabilityFacts = ctx.project.python_reachability()
    roots: set[PythonSymbolId] = {
        entry.symbol for entry in facts.entrypoints if entry.symbol is not None
    }
    stale: list[int] = []
    for index, configured in enumerate(ctx.project.dead_code.roots):
        matched: set[PythonSymbolId] = {
            symbol.id
            for symbol in facts.symbols
            if symbol.kind not in {PythonSymbolKind.MODULE, PythonSymbolKind.LOCAL}
            and matches_symbol_patterns(value=symbol.module, patterns=configured.modules)
            and matches_symbol_patterns(value=symbol.name, patterns=configured.symbols)
        }
        if not matched:
            stale.append(index)
        roots.update(matched)
    adjacency: dict[PythonSymbolId, set[PythonSymbolId]] = {}
    for reference in facts.references:
        adjacency.setdefault(reference.source, set()).add(reference.target)
    live: set[PythonSymbolId] = set()
    pending: list[PythonSymbolId] = list(roots)
    while pending:
        symbol: PythonSymbolId = pending.pop()
        if symbol in live:
            continue
        live.add(symbol)
        pending.extend(adjacency.get(symbol, ()))
    return facts, live, stale
