"""Persistent-cache behavior for typed project and tree subjects."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu import Threshold
from fensu.cache.fingerprints.models import CacheFingerprint
from fensu.cache.results.classes.result_cache import ResultCache
from fensu.cache.results.main.evaluate import evaluate_with_cache
from fensu.cache.results.models import CacheEvaluation
from fensu.config.exceptions import ConfigError
from fensu.config.models import (
    Config,
    EvaluationConfig,
    RuleExceptionEntry,
    ThresholdOverride,
)
from fensu.discovery.main.discover_files import discover_files
from fensu.discovery.models import DiscoveredTree
from fensu.rules.authoring.models import RuleSpec
from tests.integration.src.fensu.cache.results._test_types import ProjectSubjectCacheTestCase
from tests.integration.src.fensu.cache.results.helpers import (
    PROJECT_RULE_CALLS,
    cacheable_rule_spec,
    corrupt_indexed_result_record,
    evaluated_result,
    fail_project_build,
    file_graph_node_rule,
    file_position_rule,
    graph_dependencies_rule,
    graph_location_cycle_rule,
    graph_node_rule,
    graph_nodes_rule,
    project_children_rule,
    project_files_rule,
    project_location_rule,
    project_position_rule,
    project_threshold_rule,
    quiet_project_rule,
    reject_graph_build,
    source_fault_rule,
    symbol_position_rule,
    undecorated_rule_spec,
)

_FINGERPRINT: CacheFingerprint = CacheFingerprint("d" * 64)


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="zero-file project executes once across cold and warm runs",
            expected_outcome={"files": 1},
        )
    ],
    ids=lambda case: case.description,
)
def test_given_zero_files_when_project_subject_is_cached_then_cold_and_warm_run_once(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    (tmp_path / "src/example").mkdir(parents=True)
    config: Config = Config(roots=("src/example",), tests=())
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    PROJECT_RULE_CALLS.clear()

    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(cacheable_rule_spec(project_files_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(cacheable_rule_spec(project_files_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert PROJECT_RULE_CALLS == test_case.expected_outcome
    assert cold.stats.misses == 1
    assert warm.stats.hits == 1
    assert evaluated_result(cold).faults == evaluated_result(warm).faults
    assert evaluated_result(warm).project_evaluation is not None


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="narrow tree query survives unrelated inventory change",
            expected_outcome={"children": 1},
        )
    ],
    ids=lambda case: case.description,
)
def test_given_narrow_tree_query_when_unrelated_inventory_changes_then_project_hit_survives(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    orders: Path = tmp_path / "src/example/orders/models.py"
    unrelated: Path = tmp_path / "src/example/support/helpers.py"
    orders.parent.mkdir(parents=True)
    unrelated.parent.mkdir(parents=True)
    orders.write_text("", encoding="utf-8")
    unrelated.write_text("", encoding="utf-8")
    config: Config = Config(roots=("src/example",), tests=())
    initial_tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    PROJECT_RULE_CALLS.clear()
    _ = evaluate_with_cache(
        tree=initial_tree,
        ruleset=(cacheable_rule_spec(project_children_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    (tmp_path / "src/example/support/extra.py").write_text("", encoding="utf-8")
    changed_tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)

    changed: CacheEvaluation = evaluate_with_cache(
        tree=changed_tree,
        ruleset=(cacheable_rule_spec(project_children_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert PROJECT_RULE_CALLS == test_case.expected_outcome
    assert changed.stats.hits == 1


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="tree-only project rule leaves graph lazy", expected_outcome=1
        )
    ],
    ids=lambda case: case.description,
)
def test_given_custom_rule_without_graph_dependency_when_cold_and_warm_then_graph_stays_lazy(
    test_case: ProjectSubjectCacheTestCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source: Path = tmp_path / "src/example/orders/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    config: Config = Config(roots=("src/example",), tests=())
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)

    monkeypatch.setattr(
        "fensu.evaluation.main._build_architecture_graph.build_architecture_graph",
        reject_graph_build,
    )

    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(cacheable_rule_spec(project_children_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(cacheable_rule_spec(project_children_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert cold.stats.misses == test_case.expected_outcome
    assert warm.stats.hits == 1


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="narrow graph dependency survives body and unrelated edge changes",
            expected_outcome=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_graph_dependency_query_when_body_or_unrelated_edge_changes_then_narrow_hit_survives(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    entry: Path = tmp_path / "src/example/orders/entry.py"
    target: Path = tmp_path / "src/example/inventory/models.py"
    unrelated: Path = tmp_path / "src/example/support/helper.py"
    for path, source in (
        (entry, "from example.inventory import models\n"),
        (target, "VALUE = 1\n"),
        (unrelated, "VALUE = 1\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    config: Config = Config(roots=("src/example",), tests=())
    PROJECT_RULE_CALLS.clear()
    initial: CacheEvaluation = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(cacheable_rule_spec(graph_dependencies_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    target.write_text("VALUE = 2\n", encoding="utf-8")
    unrelated.write_text("import example.inventory.models\n", encoding="utf-8")

    changed: CacheEvaluation = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(cacheable_rule_spec(graph_dependencies_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert initial.stats.misses == test_case.expected_outcome
    assert changed.stats.hits == 1
    assert PROJECT_RULE_CALLS == {"graph": 1}
    assert evaluated_result(initial).faults == evaluated_result(changed).faults

    entry.write_text("import external.client\n", encoding="utf-8")
    edge_changed: CacheEvaluation = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(cacheable_rule_spec(graph_dependencies_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert edge_changed.stats.invalidations == 1
    assert PROJECT_RULE_CALLS == {"graph": 2}
    assert evaluated_result(edge_changed).faults[0].message == ""


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="broad graph query invalidates while narrow query survives",
            expected_outcome=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_broad_and_narrow_node_queries_when_inventory_changes_then_only_broad_invalidates(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    entry: Path = tmp_path / "src/example/orders/entry.py"
    entry.parent.mkdir(parents=True)
    entry.write_text("VALUE = 1\n", encoding="utf-8")
    config: Config = Config(roots=("src/example",), tests=())
    PROJECT_RULE_CALLS.clear()
    _ = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(cacheable_rule_spec(graph_node_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    extra: Path = tmp_path / "src/example/support/models.py"
    extra.parent.mkdir(parents=True)
    extra.write_text("VALUE = 2\n", encoding="utf-8")

    narrow_changed: CacheEvaluation = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(cacheable_rule_spec(graph_node_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert narrow_changed.stats.hits == 1
    assert PROJECT_RULE_CALLS == {"node": 1}

    broad_root: Path = tmp_path / "broad"
    broad_entry: Path = broad_root / "src/example/orders/entry.py"
    broad_entry.parent.mkdir(parents=True)
    broad_entry.write_text("VALUE = 1\n", encoding="utf-8")
    _ = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=broad_root),
        ruleset=(cacheable_rule_spec(graph_nodes_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    broad_extra: Path = broad_root / "src/example/support/models.py"
    broad_extra.parent.mkdir(parents=True)
    broad_extra.write_text("VALUE = 2\n", encoding="utf-8")
    broad_changed: CacheEvaluation = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=broad_root),
        ruleset=(cacheable_rule_spec(graph_nodes_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert broad_changed.stats.invalidations == test_case.expected_outcome
    assert PROJECT_RULE_CALLS == {"node": 1, "nodes": 2}
    assert evaluated_result(broad_changed).faults[0].message == "2"


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="file graph consumers retain unchanged subjects", expected_outcome=(2, 1)
        )
    ],
    ids=lambda case: case.description,
)
def test_given_file_node_consumers_when_target_added_and_removed_then_retained_subjects_survive(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    first: Path = tmp_path / "src/example/orders/models.py"
    second: Path = tmp_path / "src/example/inventory/models.py"
    for path in (first, second):
        path.parent.mkdir(parents=True)
        path.write_text("VALUE = 1\n", encoding="utf-8")
    config: Config = Config(roots=("src/example",), tests=())
    rule: RuleSpec = cacheable_rule_spec(file_graph_node_rule)
    PROJECT_RULE_CALLS.clear()
    _ = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    added: Path = tmp_path / "src/example/support/models.py"
    added.parent.mkdir(parents=True)
    added.write_text("VALUE = 1\n", encoding="utf-8")
    with_added: CacheEvaluation = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    added.unlink()
    after_removal: CacheEvaluation = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert (with_added.stats.hits, with_added.stats.misses) == test_case.expected_outcome
    assert after_removal.stats.hits == 2
    assert PROJECT_RULE_CALLS == {
        "src/example/orders/models.py": 1,
        "src/example/inventory/models.py": 1,
        "src/example/support/models.py": 1,
    }


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="nested graph replay keeps repository-relative identity", expected_outcome=1
        )
    ],
    ids=lambda case: case.description,
)
def test_given_nested_target_graph_when_replaying_then_cache_uses_repository_relative_identity(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    project_root: Path = tmp_path / "workspace"
    entry: Path = project_root / "src/example/orders/entry.py"
    target: Path = project_root / "src/example/inventory/models.py"
    entry.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    entry.write_text("from example.inventory import models\n", encoding="utf-8")
    target.write_text("from example.orders import entry\n", encoding="utf-8")
    config: Config = Config(target_root="workspace", roots=("src/example",), tests=())
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    PROJECT_RULE_CALLS.clear()

    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(cacheable_rule_spec(graph_location_cycle_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(cacheable_rule_spec(graph_location_cycle_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert cold.stats.misses == test_case.expected_outcome
    assert warm.stats.hits == 1
    assert PROJECT_RULE_CALLS == {"location-cycle": 1}
    assert evaluated_result(cold).faults == evaluated_result(warm).faults
    assert evaluated_result(cold).faults[0].path == entry
    assert {dependency.requester for dependency in evaluated_result(cold).dependencies} == {
        tmp_path / ".fensu-project-rule"
    }


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="broad inventory and position changes invalidate project rules",
            expected_outcome=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_broad_inventory_or_position_change_when_replaying_then_only_project_invalidates(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    model: Path = tmp_path / "src/example/orders/models.py"
    model.parent.mkdir(parents=True)
    model.write_text("", encoding="utf-8")
    config: Config = Config(roots=("src/example",), tests=())
    initial_tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    PROJECT_RULE_CALLS.clear()
    rules: tuple[RuleSpec, ...] = (
        cacheable_rule_spec(project_files_rule),
        cacheable_rule_spec(project_position_rule),
    )
    initial: CacheEvaluation = evaluate_with_cache(
        tree=initial_tree, ruleset=rules, config=config, global_fingerprint=_FINGERPRINT
    )
    model.rename(model.with_name("services.py"))
    changed_tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)

    changed: CacheEvaluation = evaluate_with_cache(
        tree=changed_tree, ruleset=rules, config=config, global_fingerprint=_FINGERPRINT
    )

    assert initial.stats.misses == test_case.expected_outcome
    assert changed.stats.invalidations == 1
    assert changed.stats.hits == 0
    assert PROJECT_RULE_CALLS == {"files": 2, "position": 2}
    assert tuple(fault.message for fault in evaluated_result(changed).faults) == ("1", "missing")


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="file position query survives another source edit", expected_outcome=1
        )
    ],
    ids=lambda case: case.description,
)
def test_given_file_rule_observes_own_position_when_other_source_edits_then_file_is_reused(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    own: Path = tmp_path / "src/example/orders/models.py"
    other: Path = tmp_path / "src/example/support/helpers.py"
    own.parent.mkdir(parents=True)
    other.parent.mkdir(parents=True)
    own.write_text("VALUE = 1\n", encoding="utf-8")
    other.write_text("VALUE = 1\n", encoding="utf-8")
    config: Config = Config(
        roots=("src/example",),
        tests=(),
        evaluation=EvaluationConfig(include=("src/example/orders/models.py",)),
    )
    initial_tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    PROJECT_RULE_CALLS.clear()
    _ = evaluate_with_cache(
        tree=initial_tree,
        ruleset=(cacheable_rule_spec(file_position_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    other.write_text("VALUE = 2\n", encoding="utf-8")
    changed_tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)

    changed: CacheEvaluation = evaluate_with_cache(
        tree=changed_tree,
        ruleset=(cacheable_rule_spec(file_position_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert changed.stats.hits == test_case.expected_outcome
    assert PROJECT_RULE_CALLS == {"src/example/orders/models.py": 1}


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="project warning exception replays identically",
            expected_outcome={"files": 1},
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_warning_and_file_exception_when_warm_then_replay_is_identical(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    source: Path = tmp_path / "src/example/orders/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    config: Config = Config(
        roots=("src/example",),
        tests=(),
        rule_exceptions=(
            RuleExceptionEntry(
                rule="XPC001",
                path="src/example/report.py",
                reason="project-owned repository exception",
            ),
        ),
    )
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    PROJECT_RULE_CALLS.clear()
    warning: RuleSpec = cacheable_rule_spec(project_files_rule)

    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(),
        warning_rules=(warning,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(),
        warning_rules=(warning,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert PROJECT_RULE_CALLS == test_case.expected_outcome
    assert warm.stats.hits == 1
    assert evaluated_result(cold) == evaluated_result(warm)
    assert evaluated_result(warm).warnings == ()
    assert evaluated_result(warm).applied_exception_count == 1


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="corrupt project record regenerates complete result", expected_outcome=1
        )
    ],
    ids=lambda case: case.description,
)
def test_given_corrupt_project_record_when_replaying_then_falls_back_to_fresh_project(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    source: Path = tmp_path / "src/example/orders/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    config: Config = Config(roots=("src/example",), tests=())
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    PROJECT_RULE_CALLS.clear()
    project_rule: RuleSpec = cacheable_rule_spec(project_files_rule)
    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    corrupt_indexed_result_record(repo_root=tmp_path)

    recovered: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert recovered.stats.misses == test_case.expected_outcome
    assert recovered.stats.writes == 1
    assert PROJECT_RULE_CALLS == {"files": 2}
    assert evaluated_result(recovered).faults == evaluated_result(cold).faults


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="mixed cache tiers remain separate", expected_outcome=1
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cached_file_and_fresh_project_rules_when_warm_then_tiers_stay_separate(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    source: Path = tmp_path / "src/example/orders/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    config: Config = Config(
        roots=("src/example",),
        tests=(),
        evaluation=EvaluationConfig(include=("src/example/orders/models.py",)),
    )
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    PROJECT_RULE_CALLS.clear()
    cached_file: RuleSpec = cacheable_rule_spec(file_position_rule)
    fresh_project: RuleSpec = undecorated_rule_spec(project_children_rule)

    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(cached_file, fresh_project),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(cached_file, fresh_project),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert cold.stats.misses == test_case.expected_outcome
    assert cold.stats.non_cacheable == 1
    assert warm.stats.hits == 1
    assert warm.stats.non_cacheable == 1
    assert PROJECT_RULE_CALLS == {"src/example/orders/models.py": 1, "children": 2}
    assert evaluated_result(cold).faults == evaluated_result(warm).faults


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="path reclassification invalidates project position query",
            expected_outcome=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_same_path_is_reclassified_when_replaying_position_then_project_invalidates(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    source: Path = tmp_path / "src/example/orders/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    initial_config: Config = Config(roots=("src/example",), tests=())
    changed_config: Config = Config(roots=("src/example/orders",), tests=())
    initial_tree: DiscoveredTree = discover_files(config=initial_config, repo_root=tmp_path)
    PROJECT_RULE_CALLS.clear()
    project_rule: RuleSpec = cacheable_rule_spec(project_position_rule)
    _ = evaluate_with_cache(
        tree=initial_tree,
        ruleset=(project_rule,),
        config=initial_config,
        global_fingerprint=_FINGERPRINT,
    )
    changed_tree: DiscoveredTree = discover_files(config=changed_config, repo_root=tmp_path)

    changed: CacheEvaluation = evaluate_with_cache(
        tree=changed_tree,
        ruleset=(project_rule,),
        config=changed_config,
        global_fingerprint=_FINGERPRINT,
    )

    assert changed.stats.invalidations == test_case.expected_outcome
    assert PROJECT_RULE_CALLS == {"position": 2}


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="project surface supports exact output replay", expected_outcome=(".",)
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_surface_is_stored_when_replaying_then_short_circuit_is_exact(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    (tmp_path / "src/example").mkdir(parents=True)
    config: Config = Config(roots=("src/example",), tests=())
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    project_rule: RuleSpec = cacheable_rule_spec(project_files_rule)
    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    assert cold.surface_targets == test_case.expected_outcome
    assert cold.surface_index_fingerprint is not None
    cache: ResultCache = ResultCache(repo_root=tmp_path)
    surface_targets: tuple[str, ...] | None = cold.surface_targets
    assert surface_targets is not None
    assert cache.store_check_output(
        global_fingerprint=_FINGERPRINT,
        targets=surface_targets,
        plain_output="project output\n",
        color_output="\x1b[31mproject output\x1b[0m\n",
        exit_code=1,
        expected_index_fingerprint=cold.surface_index_fingerprint,
    )

    replayed: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert replayed.result is None
    assert replayed.stats.hits == 1
    assert replayed.short_circuit is not None
    assert replayed.short_circuit.plain_output == "project output\n"
    assert replayed.short_circuit.exit_code == 1


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="file and project records replay separately", expected_outcome=2
        )
    ],
    ids=lambda case: case.description,
)
def test_given_file_and_project_subjects_when_cached_then_records_replay_separately(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    source: Path = tmp_path / "src/example/orders/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    config: Config = Config(
        roots=("src/example",),
        tests=(),
        evaluation=EvaluationConfig(include=("src/example/orders/models.py",)),
    )
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    PROJECT_RULE_CALLS.clear()
    rules: tuple[RuleSpec, ...] = (
        cacheable_rule_spec(file_position_rule),
        cacheable_rule_spec(project_children_rule),
    )

    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree, ruleset=rules, config=config, global_fingerprint=_FINGERPRINT
    )
    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree, ruleset=rules, config=config, global_fingerprint=_FINGERPRINT
    )

    assert cold.stats.misses == test_case.expected_outcome
    assert warm.stats.hits == 2
    assert PROJECT_RULE_CALLS == {"src/example/orders/models.py": 1, "children": 1}
    assert evaluated_result(cold) == evaluated_result(warm)
    assert len(evaluated_result(warm).file_evaluations) == 1
    assert evaluated_result(warm).project_evaluation is not None


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="nested tree query preserves target prefix and narrow invalidation",
            expected_outcome=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_nested_target_tree_query_when_replaying_then_prefix_and_narrowness_are_preserved(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    model: Path = tmp_path / "apps/service/src/example/orders/models.py"
    support: Path = tmp_path / "apps/service/src/example/support/helpers.py"
    model.parent.mkdir(parents=True)
    support.parent.mkdir(parents=True)
    model.write_text("", encoding="utf-8")
    support.write_text("", encoding="utf-8")
    config: Config = Config(target_root="apps/service", roots=("src/example",), tests=())
    initial_tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    PROJECT_RULE_CALLS.clear()
    project_rule: RuleSpec = cacheable_rule_spec(project_children_rule)
    cold: CacheEvaluation = evaluate_with_cache(
        tree=initial_tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm: CacheEvaluation = evaluate_with_cache(
        tree=initial_tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    (support.parent / "extra.py").write_text("", encoding="utf-8")
    unrelated_tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    unrelated: CacheEvaluation = evaluate_with_cache(
        tree=unrelated_tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    (model.parent / "service.py").write_text("", encoding="utf-8")
    relevant_tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    relevant: CacheEvaluation = evaluate_with_cache(
        tree=relevant_tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert cold.stats.misses == test_case.expected_outcome
    assert warm.stats.hits == 1
    assert unrelated.stats.hits == 1
    assert relevant.stats.invalidations == 1
    assert evaluated_result(cold) == evaluated_result(warm)
    assert evaluated_result(cold).faults == evaluated_result(unrelated).faults
    assert (
        evaluated_result(cold).project_evaluation == evaluated_result(unrelated).project_evaluation
    )
    assert PROJECT_RULE_CALLS == {"children": 2}


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="project source exception replays exactly", expected_outcome=1
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_source_location_and_symbol_exception_when_cached_then_replay_matches(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    source: Path = tmp_path / "src/example/orders/service.py"
    source.parent.mkdir(parents=True)
    source.write_text("def process() -> None:\n    return None\n", encoding="utf-8")
    config: Config = Config(
        roots=("src/example",),
        tests=(),
        rule_exceptions=(
            RuleExceptionEntry(
                rule="XPC005",
                path="src/example/orders/service.py",
                symbols=("process",),
                reason="documented project-level source exception",
            ),
        ),
    )
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    project_rule: RuleSpec = cacheable_rule_spec(project_location_rule)

    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert cold.stats.misses == test_case.expected_outcome
    assert warm.stats.hits == 1
    assert evaluated_result(cold) == evaluated_result(warm)
    assert evaluated_result(warm).faults == ()
    assert evaluated_result(warm).applied_exception_count == 1


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="moved symbol invalidates cached suppression", expected_outcome=1
        )
    ],
    ids=lambda case: case.description,
)
def test_given_symbol_exception_source_moves_when_replaying_then_suppression_invalidates(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    source: Path = tmp_path / "src/example/orders/service.py"
    source.parent.mkdir(parents=True)
    source.write_text("def process() -> None:\n    return None\n", encoding="utf-8")

    config: Config = Config(
        roots=("src/example",),
        tests=(),
        rule_exceptions=(
            RuleExceptionEntry(
                rule="XPC013",
                path="src/example/orders/service.py",
                symbols=("process",),
                reason="symbol location must be revalidated",
            ),
        ),
    )
    project_rule: RuleSpec = symbol_position_rule(source=source)
    cold: CacheEvaluation = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    source.write_text("# shifted\ndef process() -> None:\n    return None\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="Stale rule exception"):
        evaluate_with_cache(
            tree=discover_files(config=config, repo_root=tmp_path),
            ruleset=(project_rule,),
            config=config,
            global_fingerprint=_FINGERPRINT,
        )

    assert cold.stats.misses == test_case.expected_outcome
    assert evaluated_result(cold).faults == ()


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="nested project exception matches target-relative source",
            expected_outcome=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_nested_project_symbol_exception_when_evaluating_then_matches_target_relative_path(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    source: Path = tmp_path / "apps/service/src/example/orders/service.py"
    source.parent.mkdir(parents=True)
    source.write_text("def process() -> None:\n    return None\n", encoding="utf-8")
    config: Config = Config(
        target_root="apps/service",
        roots=("src/example",),
        tests=(),
        rule_exceptions=(
            RuleExceptionEntry(
                rule="XPC005",
                path="src/example/orders/service.py",
                symbols=("process",),
                reason="documented nested project exception",
            ),
        ),
    )
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)

    result: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(cacheable_rule_spec(project_location_rule),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert evaluated_result(result).faults == ()
    assert evaluated_result(result).applied_exception_count == test_case.expected_outcome


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="filtered project still validates stale exception",
            expected_outcome="Stale rule exception",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_filtered_files_and_stale_project_exception_when_evaluating_then_reports_stale(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    selected: Path = tmp_path / "src/example/selected.py"
    excluded: Path = tmp_path / "src/example/excluded.py"
    selected.parent.mkdir(parents=True)
    selected.write_text("", encoding="utf-8")
    excluded.write_text("", encoding="utf-8")
    config: Config = Config(
        roots=("src/example",),
        tests=(),
        evaluation=EvaluationConfig(include=("src/example/selected.py",)),
        rule_exceptions=(
            RuleExceptionEntry(
                rule="XPC012",
                path="src/example/excluded.py",
                reason="project exception must remain live during a scoped run",
            ),
        ),
    )
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)

    with pytest.raises(ConfigError, match=str(test_case.expected_outcome)):
        evaluate_with_cache(
            tree=tree,
            ruleset=(cacheable_rule_spec(quiet_project_rule),),
            config=config,
            global_fingerprint=_FINGERPRINT,
        )


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="project threshold override use replays exactly", expected_outcome=1
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_threshold_override_when_cached_then_use_replays_exactly(
    test_case: ProjectSubjectCacheTestCase,
    tmp_path: Path,
) -> None:
    source: Path = tmp_path / "src/example/orders/service.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    config: Config = Config(
        roots=("src/example",),
        tests=(),
        test_scopes=("unit",),
        threshold_overrides=(
            ThresholdOverride(
                paths=("src/example/orders/*.py",),
                thresholds={Threshold.MAX_FILE_LINES: 7},
                reason="generated integration boundary",
            ),
        ),
    )
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    project_rule: RuleSpec = cacheable_rule_spec(project_threshold_rule)

    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert warm.stats.hits == test_case.expected_outcome
    assert evaluated_result(cold) == evaluated_result(warm)
    assert evaluated_result(warm).faults[0].message == "7"
    assert len(evaluated_result(warm).threshold_override_uses) == 1


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectSubjectCacheTestCase(
            description="warm core-only replay leaves project analysis lazy", expected_outcome=1
        )
    ],
    ids=lambda case: case.description,
)
def test_given_warm_core_only_result_when_replaying_then_project_tree_is_not_built(
    test_case: ProjectSubjectCacheTestCase,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source: Path = tmp_path / "src/example/orders/service.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    config: Config = Config(roots=("src/example",), tests=())
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    core_rule: RuleSpec = source_fault_rule()
    _ = evaluate_with_cache(
        tree=tree,
        ruleset=(core_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    import fensu.evaluation.main.build_project as build_project_module

    monkeypatch.setattr(build_project_module, "build_evaluation_project", fail_project_build)

    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(core_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert warm.stats.hits == test_case.expected_outcome
