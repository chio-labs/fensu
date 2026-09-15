"""Behavior tests for analyzer-neutral architecture graph facts."""

from pathlib import Path

from fensu import (
    Family,
    Fault,
    File,
    ImportResolution,
    ModuleVisibility,
    Project,
    ProjectPath,
    RuleCase,
    RuleContext,
    RuleFile,
    evaluate_rule,
    rule,
)
from fensu.config.models import Config
from fensu.discovery.main.discover_files import discover_files
from fensu.evaluation.main.build_project import build_evaluation_project
from fensu.rules.exemplars.main.layers._no_cross_package_internals import (
    no_cross_package_internals_equivalent,
)

_INVOCATIONS: list[int] = []


@rule(
    code="XAG001",
    family=Family.CUSTOM,
    slug="architecture-graph-facts",
    message="architecture graph",
)
def architecture_graph_rule(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Prove resolution, ownership, reverse edges, unresolved facts, and cycle order."""

    del project
    _INVOCATIONS.append(1)
    by_module = {node.module: node for node in ctx.graph.nodes}
    entry = by_module["shop.orders.main.entry"]
    helper = by_module["shop.orders.main.helper"]
    imports = ctx.graph.imports(entry)

    assert tuple(edge.target.module if edge.target else None for edge in imports) == (
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
    inventory = by_module["shop.inventory.models"]
    assert inventory.domain_parts == ("inventory",)
    assert inventory.role == "models"
    internal = by_module["shop.support._helpers.tool"]
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
    assert tuple(tuple(node.module for node in cycle.nodes) for cycle in ctx.graph.cycles()) == (
        ("shop.orders.main.entry", "shop.orders.main.helper"),
    )
    return [ctx.fault_at(location=imports[1].location)]


@rule(
    code="XAG002",
    family=Family.CUSTOM,
    slug="file-architecture-graph",
    message="file architecture graph",
)
def file_architecture_graph_rule(*, file: File, ctx: RuleContext) -> list[Fault]:
    """Use the same graph surface from a typed file callback."""

    dependencies = ctx.graph.dependencies(file)
    if file.path.name != "entry.py":
        return []
    assert tuple(node.module for node in dependencies) == ("shop.inventory.models",)
    return [ctx.path_fault()]


def test_given_static_python_imports_when_querying_project_graph_then_returns_resolved_facts_once() -> (
    None
):
    _INVOCATIONS.clear()
    case = RuleCase(
        description="resolved project graph",
        source=(
            "import shop.inventory.models as inventory\n"
            "from shop.catalog import service\n"
            "from shop.catalog import missing_symbol\n"
            "from shop import catalog\n"
            "from . import helper\n"
            "import external.client\n"
            "import shop.support._helpers.tool\n"
        ),
        path="src/shop/orders/main/entry.py",
        expected_fault_count=1,
        files=(
            RuleFile(path="src/shop/__init__.py", source=""),
            RuleFile(path="src/shop/catalog/__init__.py", source=""),
            RuleFile(path="src/shop/catalog/service.py", source=""),
            RuleFile(path="src/shop/inventory/models.py", source=""),
            RuleFile(path="src/shop/support/_helpers/tool.py", source=""),
            RuleFile(
                path="src/shop/orders/main/helper.py",
                source="from shop.orders.main import entry\n",
            ),
        ),
    )

    result = evaluate_rule(rule=architecture_graph_rule, test_case=case)

    assert result.fault_count == 1
    assert _INVOCATIONS == [1]
    assert {dependency.kind for dependency in result.dependencies} == {
        "graph_cycles",
        "graph_dependencies",
        "graph_dependents",
        "graph_imports",
        "graph_nodes",
    }


def test_given_typed_file_rule_when_querying_graph_then_uses_file_identity() -> None:
    case = RuleCase(
        description="file graph identity",
        source="from shop.inventory import models\n",
        path="src/shop/orders/entry.py",
        expected_fault_count=1,
        files=(RuleFile(path="src/shop/inventory/models.py", source=""),),
    )

    result = evaluate_rule(rule=file_architecture_graph_rule, test_case=case)

    assert result.fault_count == 1


def test_given_duplicate_discovered_module_names_when_resolving_then_import_stays_unresolved(
    tmp_path: Path,
) -> None:
    first = tmp_path / "src/first/example"
    second = tmp_path / "src/second/example"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (first / "consumer.py").write_text("import example.target\n", encoding="utf-8")
    (first / "target.py").write_text("FIRST = 1\n", encoding="utf-8")
    (second / "target.py").write_text("SECOND = 2\n", encoding="utf-8")
    config = Config(roots=("src/first/example", "src/second/example"), tests=())
    tree = discover_files(config=config, repo_root=tmp_path)
    analysis = build_evaluation_project(tree=tree)
    graph = analysis.architecture_graph(requester=first / "consumer.py")
    consumer = graph.node(ProjectPath("src/first/example/consumer.py"))
    assert consumer is not None

    edges = graph.imports(consumer)

    assert len(edges) == 1
    assert edges[0].status is ImportResolution.UNRESOLVED
    assert edges[0].target is None


def test_given_multi_alias_internal_import_when_checking_exemplar_then_reports_statement_once() -> (
    None
):
    case = RuleCase(
        description="multi-alias internal import",
        source="from example.inventory._helpers import first, second\n",
        path="src/example/orders/service.py",
        expected_fault_count=1,
        files=(RuleFile(path="src/example/inventory/_helpers/__init__.py", source=""),),
    )

    result = evaluate_rule(rule=no_cross_package_internals_equivalent, test_case=case)

    assert result.fault_count == 1


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-vv"])
