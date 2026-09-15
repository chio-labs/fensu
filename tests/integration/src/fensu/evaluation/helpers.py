"""Rule callbacks for architecture graph integration tests."""

from __future__ import annotations

from collections.abc import Callable

from fensu import (
    Family,
    Fault,
    File,
    ImportEdge,
    ImportResolution,
    ModuleNode,
    ModuleVisibility,
    Project,
    RuleContext,
    rule,
)

ARCHITECTURE_GRAPH_INVOCATIONS: list[int] = []


def reset_architecture_graph_invocations() -> None:
    """Reset the project callback invocation probe."""

    ARCHITECTURE_GRAPH_INVOCATIONS.clear()


def _cycle_modules(ctx: RuleContext) -> tuple[tuple[str, ...], ...]:
    modules: list[tuple[str, ...]] = []
    for cycle in ctx.graph.cycles():
        modules.append(tuple(node.module for node in cycle.nodes))
    return tuple(modules)


@rule(
    code="XAG001",
    family=Family.CUSTOM,
    slug="architecture-graph-facts",
    message="architecture graph",
)
def architecture_graph_rule(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Prove resolution, ownership, reverse edges, unresolved facts, and cycle order."""

    del project
    ARCHITECTURE_GRAPH_INVOCATIONS.append(1)
    by_module: dict[str, ModuleNode] = {node.module: node for node in ctx.graph.nodes}
    entry: ModuleNode = by_module["shop.orders.main.entry"]
    helper: ModuleNode = by_module["shop.orders.main.helper"]
    imports: tuple[ImportEdge, ...] = ctx.graph.imports(entry)

    assert tuple(getattr(edge.target, "module", None) for edge in imports) == (
        "shop.inventory.models",
        "shop.catalog.service",
        "shop.catalog",
        "shop.catalog",
        "shop.orders.main.helper",
        None,
        "shop.support._helpers.tool",
    )
    assert imports[-2].status is ImportResolution.UNRESOLVED
    assert imports[-2].authored.imported_parts == ("external", "client")
    assert imports[-2].module == "external.client"
    assert imports[1].location.path.as_posix().endswith("src/shop/orders/main/entry.py")
    assert imports[1].location.line == 2
    assert entry.scope.value == "root"
    assert entry.analyzer.value == "python"
    assert entry.source_kind.value == "python_module"
    assert entry.package == "shop.orders.main"
    assert entry.domain_parts == ("orders",)
    assert entry.role == "main"
    assert entry.visibility is ModuleVisibility.PUBLIC
    inventory: ModuleNode = by_module["shop.inventory.models"]
    assert inventory.domain_parts == ("inventory",)
    assert inventory.role == "models"
    internal: ModuleNode = by_module["shop.support._helpers.tool"]
    assert internal.domain_parts == ("support",)
    assert internal.role == "helpers"
    assert internal.visibility is ModuleVisibility.INTERNAL
    assert ctx.graph.dependencies(entry) == (
        by_module["shop.catalog"],
        by_module["shop.catalog.service"],
        inventory,
        helper,
        internal,
    )
    assert ctx.graph.dependents(helper) == (entry,)
    assert _cycle_modules(ctx) == (("shop.orders.main.entry", "shop.orders.main.helper"),)
    return [ctx.fault_at(location=imports[1].location)]


def _entry_file_fault(*, ctx: RuleContext, dependencies: tuple[ModuleNode, ...]) -> list[Fault]:
    assert tuple(node.module for node in dependencies) == ("shop.inventory.models",)
    return [ctx.path_fault()]


def _other_file_fault(*, ctx: RuleContext, dependencies: tuple[ModuleNode, ...]) -> list[Fault]:
    del ctx, dependencies
    return []


_FILE_FAULTS: dict[str, Callable[..., list[Fault]]] = {"entry.py": _entry_file_fault}


@rule(
    code="XAG002",
    family=Family.CUSTOM,
    slug="file-architecture-graph",
    message="file architecture graph",
)
def file_architecture_graph_rule(*, file: File, ctx: RuleContext) -> list[Fault]:
    """Use the same graph surface from a typed file callback."""

    dependencies: tuple[ModuleNode, ...] = ctx.graph.dependencies(file)
    fault: Callable[..., list[Fault]] = _FILE_FAULTS.get(file.path.name, _other_file_fault)
    return fault(ctx=ctx, dependencies=dependencies)
