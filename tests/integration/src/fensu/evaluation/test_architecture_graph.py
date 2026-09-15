"""Behavior tests for analyzer-neutral architecture graph facts."""

from pathlib import Path

import pytest

from fensu import (
    ArchitectureGraph,
    ImportEdge,
    ImportResolution,
    ModuleNode,
    ProjectPath,
    RuleCase,
    RuleFile,
    RuleResult,
    evaluate_rule,
)
from fensu.config.models import Config
from fensu.discovery.main.discover_files import discover_files
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation.main.build_project import build_evaluation_project
from fensu.evaluation.types import EvaluationProjectAnalysis
from fensu.rules.exemplars.main.layers._no_cross_package_internals import (
    no_cross_package_internals_equivalent,
)
from tests.integration.src.fensu.evaluation._test_types import (
    AmbiguousModuleGraphTestCase,
    FileArchitectureGraphTestCase,
    MultiAliasGraphParityTestCase,
    ProjectArchitectureGraphTestCase,
)
from tests.integration.src.fensu.evaluation.helpers import (
    ARCHITECTURE_GRAPH_INVOCATIONS,
    architecture_graph_rule,
    file_architecture_graph_rule,
    reset_architecture_graph_invocations,
)


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectArchitectureGraphTestCase(
            description="static imports expose resolved project graph facts once",
            rule_case=RuleCase(
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
            ),
            expected_fault_count=1,
            expected_invocations=(1,),
            expected_dependency_kinds=frozenset(
                {
                    "graph_cycles",
                    "graph_dependencies",
                    "graph_dependents",
                    "graph_imports",
                    "graph_nodes",
                }
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_static_python_imports_when_querying_project_graph_then_returns_resolved_facts_once(
    test_case: ProjectArchitectureGraphTestCase,
) -> None:
    reset_architecture_graph_invocations()

    result: RuleResult = evaluate_rule(rule=architecture_graph_rule, test_case=test_case.rule_case)

    assert result.fault_count == test_case.expected_fault_count
    assert tuple(ARCHITECTURE_GRAPH_INVOCATIONS) == test_case.expected_invocations
    assert {
        dependency.kind for dependency in result.dependencies
    } == test_case.expected_dependency_kinds


@pytest.mark.parametrize(
    "test_case",
    [
        FileArchitectureGraphTestCase(
            description="typed file rule uses the file graph identity",
            rule_case=RuleCase(
                description="file graph identity",
                source="from shop.inventory import models\n",
                path="src/shop/orders/entry.py",
                expected_fault_count=1,
                files=(RuleFile(path="src/shop/inventory/models.py", source=""),),
            ),
            expected_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_typed_file_rule_when_querying_graph_then_uses_file_identity(
    test_case: FileArchitectureGraphTestCase,
) -> None:
    result: RuleResult = evaluate_rule(
        rule=file_architecture_graph_rule, test_case=test_case.rule_case
    )

    assert result.fault_count == test_case.expected_fault_count


@pytest.mark.parametrize(
    "test_case",
    [
        AmbiguousModuleGraphTestCase(
            description="duplicate discovered module names remain unresolved",
            expected_edge_count=1,
            expected_resolution=ImportResolution.UNRESOLVED,
            expected_target=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_duplicate_discovered_module_names_when_resolving_then_import_stays_unresolved(
    tmp_path: Path,
    test_case: AmbiguousModuleGraphTestCase,
) -> None:
    first: Path = tmp_path / "src/first/example"
    second: Path = tmp_path / "src/second/example"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (first / "consumer.py").write_text("import example.target\n", encoding="utf-8")
    (first / "target.py").write_text("FIRST = 1\n", encoding="utf-8")
    (second / "target.py").write_text("SECOND = 2\n", encoding="utf-8")
    config: Config = Config(roots=("src/first/example", "src/second/example"), tests=())
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    analysis: EvaluationProjectAnalysis = build_evaluation_project(tree=tree)
    graph: ArchitectureGraph = analysis.architecture_graph(requester=first / "consumer.py")
    consumer: ModuleNode | None = graph.node(ProjectPath("src/first/example/consumer.py"))
    assert consumer is not None

    edges: tuple[ImportEdge, ...] = graph.imports(consumer)

    assert len(edges) == test_case.expected_edge_count
    assert edges[0].status == test_case.expected_resolution
    assert edges[0].target is test_case.expected_target


@pytest.mark.parametrize(
    "test_case",
    [
        MultiAliasGraphParityTestCase(
            description="multi-alias internal import reports its statement once",
            rule_case=RuleCase(
                description="multi-alias internal import",
                source="from example.inventory._helpers import first, second\n",
                path="src/example/orders/service.py",
                expected_fault_count=1,
                files=(RuleFile(path="src/example/inventory/_helpers/__init__.py", source=""),),
            ),
            expected_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_multi_alias_internal_import_when_checking_exemplar_then_reports_statement_once(
    test_case: MultiAliasGraphParityTestCase,
) -> None:
    result: RuleResult = evaluate_rule(
        rule=no_cross_package_internals_equivalent,
        test_case=test_case.rule_case,
    )

    assert result.fault_count == test_case.expected_fault_count


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
