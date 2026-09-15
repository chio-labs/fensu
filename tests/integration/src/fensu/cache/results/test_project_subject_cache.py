"""Persistent-cache behavior for typed project and tree subjects."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from fensu import Family, Fault, File, Project, ProjectPath, RuleContext, Threshold, rule
from fensu.analysis.models import SourceLocation
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
from fensu.evaluation.models import EvaluationResult
from fensu.rules.authoring.constants import _RULE_SPEC_ATTRIBUTE
from fensu.rules.authoring.models import RuleSpec
from tests.integration.src.fensu.cache.results.helpers import (
    corrupt_indexed_result_record,
    source_fault_rule,
)

_FINGERPRINT = CacheFingerprint("d" * 64)
_CALLS: dict[str, int] = {}


def _called(name: str) -> None:
    _CALLS[name] = _CALLS.get(name, 0) + 1


@rule(code="XPC001", family=Family.CUSTOM, slug="project-files", message="project files")
def _project_files(*, project: Project, ctx: RuleContext) -> list[Fault]:
    del project
    _called("files")
    return [ctx.path_fault(path="src/example/report.py", message=str(len(ctx.project.tree.files)))]


@rule(code="XPC002", family=Family.CUSTOM, slug="project-children", message="project children")
def _project_children(*, project: Project, ctx: RuleContext) -> list[Fault]:
    del project
    _called("children")
    names = ",".join(path.name for path in ctx.project.tree.children("src/example/orders"))
    return [ctx.path_fault(path="src/example/report.py", message=names)]


@rule(code="XPC003", family=Family.CUSTOM, slug="project-position", message="project position")
def _project_position(*, project: Project, ctx: RuleContext) -> list[Fault]:
    del project
    _called("position")
    position = ctx.project.tree.position("src/example/orders/models.py")
    return [
        ctx.path_fault(
            path="src/example/report.py",
            message="missing" if position is None else f"{position.role}:{position.role_depth}",
        )
    ]


@rule(code="XPC004", family=Family.CUSTOM, slug="file-position", message="file position")
def _file_position(*, file: File, ctx: RuleContext) -> list[Fault]:
    _called(file.path.value)
    position = ctx.project.tree.position(file.path)
    assert position is not None
    return [ctx.path_fault(message=position.scope_root.value)]


@rule(code="XPC005", family=Family.CUSTOM, slug="project-location", message="location")
def _project_location(*, project: Project, ctx: RuleContext) -> list[Fault]:
    del project
    analysis = ctx.project.analysis(path=ProjectPath("src/example/orders/service.py"))
    assert analysis is not None
    handle = analysis.syntax.handles()[0]
    return [ctx.fault_at(location=SourceLocation(path=handle.path, line=2, column=4))]


@rule(code="XPC006", family=Family.CUSTOM, slug="project-threshold", message="threshold")
def _project_threshold(*, project: Project, ctx: RuleContext) -> list[Fault]:
    del project
    assert ctx.contracts()
    assert ctx.test_scopes()
    value = ctx.threshold(name=Threshold.MAX_FILE_LINES, path="src/example/orders/service.py")
    return [ctx.path_fault(path="src/example/orders/service.py", message=str(value))]


@rule(code="XPC007", family=Family.CUSTOM, slug="graph-dependencies", message="dependencies")
def _graph_dependencies(*, project: Project, ctx: RuleContext) -> list[Fault]:
    del project
    _called("graph")
    entry = ctx.graph.node(ProjectPath("src/example/orders/entry.py"))
    assert entry is not None
    modules = ",".join(node.module for node in ctx.graph.dependencies(entry))
    return [ctx.path_fault(path=entry.file.path, message=modules)]


@rule(code="XPC008", family=Family.CUSTOM, slug="graph-nodes", message="nodes")
def _graph_nodes(*, project: Project, ctx: RuleContext) -> list[Fault]:
    del project
    _called("nodes")
    return [ctx.path_fault(path="src/example/orders/entry.py", message=str(len(ctx.graph.nodes)))]


@rule(code="XPC009", family=Family.CUSTOM, slug="graph-node", message="node")
def _graph_node(*, project: Project, ctx: RuleContext) -> list[Fault]:
    del project
    _called("node")
    node = ctx.graph.node(ProjectPath("src/example/orders/entry.py"))
    assert node is not None
    return [ctx.path_fault(path=node.file.path, message=node.module)]


@rule(code="XPC010", family=Family.CUSTOM, slug="graph-location-cycle", message="graph")
def _graph_location_cycle(*, project: Project, ctx: RuleContext) -> list[Fault]:
    del project
    _called("location-cycle")
    node = ctx.graph.node(ProjectPath("src/example/orders/entry.py"))
    assert node is not None
    edge = ctx.graph.imports(node)[0]
    assert ctx.graph.cycles()
    return [ctx.fault_at(location=edge.location)]


@rule(code="XPC011", family=Family.CUSTOM, slug="file-graph-node", message="node")
def _file_graph_node(*, file: File, ctx: RuleContext) -> list[Fault]:
    _called(file.path.value)
    node = ctx.graph.node(file)
    assert node is not None
    return [ctx.path_fault(message=node.module)]


@rule(code="XPC012", family=Family.CUSTOM, slug="quiet-project", message="quiet project")
def _quiet_project(*, project: Project, ctx: RuleContext) -> list[Fault]:
    del project, ctx
    return []


def _spec(callback: object) -> RuleSpec:
    return replace(getattr(callback, _RULE_SPEC_ATTRIBUTE), cacheable=True)


def _result(value: CacheEvaluation) -> EvaluationResult:
    result = value.result
    assert isinstance(result, EvaluationResult)
    return result


def test_given_zero_files_when_project_subject_is_cached_then_cold_and_warm_run_once(
    tmp_path: Path,
) -> None:
    (tmp_path / "src/example").mkdir(parents=True)
    config = Config(roots=("src/example",), tests=())
    tree = discover_files(config=config, repo_root=tmp_path)
    _CALLS.clear()

    cold = evaluate_with_cache(
        tree=tree, ruleset=(_spec(_project_files),), config=config, global_fingerprint=_FINGERPRINT
    )
    warm = evaluate_with_cache(
        tree=tree, ruleset=(_spec(_project_files),), config=config, global_fingerprint=_FINGERPRINT
    )

    assert _CALLS == {"files": 1}
    assert cold.stats.misses == 1
    assert warm.stats.hits == 1
    assert _result(cold).faults == _result(warm).faults
    assert _result(warm).project_evaluation is not None


def test_given_narrow_tree_query_when_unrelated_inventory_changes_then_project_hit_survives(
    tmp_path: Path,
) -> None:
    orders = tmp_path / "src/example/orders/models.py"
    unrelated = tmp_path / "src/example/support/helpers.py"
    orders.parent.mkdir(parents=True)
    unrelated.parent.mkdir(parents=True)
    orders.write_text("", encoding="utf-8")
    unrelated.write_text("", encoding="utf-8")
    config = Config(roots=("src/example",), tests=())
    initial_tree = discover_files(config=config, repo_root=tmp_path)
    _CALLS.clear()
    _ = evaluate_with_cache(
        tree=initial_tree,
        ruleset=(_spec(_project_children),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    (tmp_path / "src/example/support/extra.py").write_text("", encoding="utf-8")
    changed_tree = discover_files(config=config, repo_root=tmp_path)

    changed = evaluate_with_cache(
        tree=changed_tree,
        ruleset=(_spec(_project_children),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert _CALLS == {"children": 1}
    assert changed.stats.hits == 1


def test_given_custom_rule_without_graph_dependency_when_cold_and_warm_then_graph_stays_lazy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "src/example/orders/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    config = Config(roots=("src/example",), tests=())
    tree = discover_files(config=config, repo_root=tmp_path)

    def reject_graph_build(**kwargs: object) -> None:
        del kwargs
        raise AssertionError("graph was built without a graph query")

    monkeypatch.setattr(
        "fensu.evaluation._helpers.architecture_graph.build_architecture_graph",
        reject_graph_build,
    )

    cold = evaluate_with_cache(
        tree=tree,
        ruleset=(_spec(_project_children),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm = evaluate_with_cache(
        tree=tree,
        ruleset=(_spec(_project_children),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert cold.stats.misses == 1
    assert warm.stats.hits == 1


def test_given_graph_dependency_query_when_body_or_unrelated_edge_changes_then_narrow_hit_survives(
    tmp_path: Path,
) -> None:
    entry = tmp_path / "src/example/orders/entry.py"
    target = tmp_path / "src/example/inventory/models.py"
    unrelated = tmp_path / "src/example/support/helper.py"
    for path, source in (
        (entry, "from example.inventory import models\n"),
        (target, "VALUE = 1\n"),
        (unrelated, "VALUE = 1\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    config = Config(roots=("src/example",), tests=())
    _CALLS.clear()
    initial = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(_spec(_graph_dependencies),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    target.write_text("VALUE = 2\n", encoding="utf-8")
    unrelated.write_text("import example.inventory.models\n", encoding="utf-8")

    changed = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(_spec(_graph_dependencies),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert initial.stats.misses == 1
    assert changed.stats.hits == 1
    assert _CALLS == {"graph": 1}
    assert _result(initial).faults == _result(changed).faults

    entry.write_text("import external.client\n", encoding="utf-8")
    edge_changed = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(_spec(_graph_dependencies),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert edge_changed.stats.invalidations == 1
    assert _CALLS == {"graph": 2}
    assert _result(edge_changed).faults[0].message == ""


def test_given_broad_and_narrow_node_queries_when_inventory_changes_then_only_broad_invalidates(
    tmp_path: Path,
) -> None:
    entry = tmp_path / "src/example/orders/entry.py"
    entry.parent.mkdir(parents=True)
    entry.write_text("VALUE = 1\n", encoding="utf-8")
    config = Config(roots=("src/example",), tests=())
    _CALLS.clear()
    _ = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(_spec(_graph_node),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    extra = tmp_path / "src/example/support/models.py"
    extra.parent.mkdir(parents=True)
    extra.write_text("VALUE = 2\n", encoding="utf-8")

    narrow_changed = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(_spec(_graph_node),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert narrow_changed.stats.hits == 1
    assert _CALLS == {"node": 1}

    broad_root = tmp_path / "broad"
    broad_entry = broad_root / "src/example/orders/entry.py"
    broad_entry.parent.mkdir(parents=True)
    broad_entry.write_text("VALUE = 1\n", encoding="utf-8")
    _ = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=broad_root),
        ruleset=(_spec(_graph_nodes),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    broad_extra = broad_root / "src/example/support/models.py"
    broad_extra.parent.mkdir(parents=True)
    broad_extra.write_text("VALUE = 2\n", encoding="utf-8")
    broad_changed = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=broad_root),
        ruleset=(_spec(_graph_nodes),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert broad_changed.stats.invalidations == 1
    assert _CALLS == {"node": 1, "nodes": 2}
    assert _result(broad_changed).faults[0].message == "2"


def test_given_file_node_consumers_when_target_added_and_removed_then_retained_subjects_survive(
    tmp_path: Path,
) -> None:
    first = tmp_path / "src/example/orders/models.py"
    second = tmp_path / "src/example/inventory/models.py"
    for path in (first, second):
        path.parent.mkdir(parents=True)
        path.write_text("VALUE = 1\n", encoding="utf-8")
    config = Config(roots=("src/example",), tests=())
    rule = _spec(_file_graph_node)
    _CALLS.clear()
    _ = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    added = tmp_path / "src/example/support/models.py"
    added.parent.mkdir(parents=True)
    added.write_text("VALUE = 1\n", encoding="utf-8")
    with_added = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    added.unlink()
    after_removal = evaluate_with_cache(
        tree=discover_files(config=config, repo_root=tmp_path),
        ruleset=(rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert (with_added.stats.hits, with_added.stats.misses) == (2, 1)
    assert after_removal.stats.hits == 2
    assert _CALLS == {
        "src/example/orders/models.py": 1,
        "src/example/inventory/models.py": 1,
        "src/example/support/models.py": 1,
    }


def test_given_nested_target_graph_when_replaying_then_cache_uses_repository_relative_identity(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "workspace"
    entry = project_root / "src/example/orders/entry.py"
    target = project_root / "src/example/inventory/models.py"
    entry.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    entry.write_text("from example.inventory import models\n", encoding="utf-8")
    target.write_text("from example.orders import entry\n", encoding="utf-8")
    config = Config(target_root="workspace", roots=("src/example",), tests=())
    tree = discover_files(config=config, repo_root=tmp_path)
    _CALLS.clear()

    cold = evaluate_with_cache(
        tree=tree,
        ruleset=(_spec(_graph_location_cycle),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm = evaluate_with_cache(
        tree=tree,
        ruleset=(_spec(_graph_location_cycle),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert cold.stats.misses == 1
    assert warm.stats.hits == 1
    assert _CALLS == {"location-cycle": 1}
    assert _result(cold).faults == _result(warm).faults
    assert _result(cold).faults[0].path == entry
    assert {dependency.requester for dependency in _result(cold).dependencies} == {
        tmp_path / ".fensu-project-rule"
    }


def test_given_broad_inventory_or_position_change_when_replaying_then_only_project_invalidates(
    tmp_path: Path,
) -> None:
    model = tmp_path / "src/example/orders/models.py"
    model.parent.mkdir(parents=True)
    model.write_text("", encoding="utf-8")
    config = Config(roots=("src/example",), tests=())
    initial_tree = discover_files(config=config, repo_root=tmp_path)
    _CALLS.clear()
    rules = (_spec(_project_files), _spec(_project_position))
    initial = evaluate_with_cache(
        tree=initial_tree, ruleset=rules, config=config, global_fingerprint=_FINGERPRINT
    )
    model.rename(model.with_name("services.py"))
    changed_tree = discover_files(config=config, repo_root=tmp_path)

    changed = evaluate_with_cache(
        tree=changed_tree, ruleset=rules, config=config, global_fingerprint=_FINGERPRINT
    )

    assert initial.stats.misses == 1
    assert changed.stats.invalidations == 1
    assert changed.stats.hits == 0
    assert _CALLS == {"files": 2, "position": 2}
    assert tuple(fault.message for fault in _result(changed).faults) == ("1", "missing")


def test_given_file_rule_observes_own_position_when_other_source_edits_then_file_is_reused(
    tmp_path: Path,
) -> None:
    own = tmp_path / "src/example/orders/models.py"
    other = tmp_path / "src/example/support/helpers.py"
    own.parent.mkdir(parents=True)
    other.parent.mkdir(parents=True)
    own.write_text("VALUE = 1\n", encoding="utf-8")
    other.write_text("VALUE = 1\n", encoding="utf-8")
    config = Config(
        roots=("src/example",),
        tests=(),
        evaluation=EvaluationConfig(include=("src/example/orders/models.py",)),
    )
    initial_tree = discover_files(config=config, repo_root=tmp_path)
    _CALLS.clear()
    _ = evaluate_with_cache(
        tree=initial_tree,
        ruleset=(_spec(_file_position),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    other.write_text("VALUE = 2\n", encoding="utf-8")
    changed_tree = discover_files(config=config, repo_root=tmp_path)

    changed = evaluate_with_cache(
        tree=changed_tree,
        ruleset=(_spec(_file_position),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert changed.stats.hits == 1
    assert _CALLS == {"src/example/orders/models.py": 1}


def test_given_project_warning_and_file_exception_when_warm_then_replay_is_identical(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/example/orders/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    config = Config(
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
    tree = discover_files(config=config, repo_root=tmp_path)
    _CALLS.clear()
    warning = _spec(_project_files)

    cold = evaluate_with_cache(
        tree=tree,
        ruleset=(),
        warning_rules=(warning,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm = evaluate_with_cache(
        tree=tree,
        ruleset=(),
        warning_rules=(warning,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert _CALLS == {"files": 1}
    assert warm.stats.hits == 1
    assert _result(cold) == _result(warm)
    assert _result(warm).warnings == ()
    assert _result(warm).applied_exception_count == 1


def test_given_corrupt_project_record_when_replaying_then_falls_back_to_fresh_project(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/example/orders/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    config = Config(roots=("src/example",), tests=())
    tree = discover_files(config=config, repo_root=tmp_path)
    _CALLS.clear()
    project_rule = _spec(_project_files)
    cold = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    corrupt_indexed_result_record(repo_root=tmp_path)

    recovered = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert recovered.stats.misses == 1
    assert recovered.stats.writes == 1
    assert _CALLS == {"files": 2}
    assert _result(recovered).faults == _result(cold).faults


def test_given_cached_file_and_fresh_project_rules_when_warm_then_tiers_stay_separate(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/example/orders/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    config = Config(
        roots=("src/example",),
        tests=(),
        evaluation=EvaluationConfig(include=("src/example/orders/models.py",)),
    )
    tree = discover_files(config=config, repo_root=tmp_path)
    _CALLS.clear()
    cached_file = _spec(_file_position)
    fresh_project = getattr(_project_children, _RULE_SPEC_ATTRIBUTE)

    cold = evaluate_with_cache(
        tree=tree,
        ruleset=(cached_file, fresh_project),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm = evaluate_with_cache(
        tree=tree,
        ruleset=(cached_file, fresh_project),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert cold.stats.misses == 1
    assert cold.stats.non_cacheable == 1
    assert warm.stats.hits == 1
    assert warm.stats.non_cacheable == 1
    assert _CALLS == {"src/example/orders/models.py": 1, "children": 2}
    assert _result(cold).faults == _result(warm).faults


def test_given_same_path_is_reclassified_when_replaying_position_then_project_invalidates(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/example/orders/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    initial_config = Config(roots=("src/example",), tests=())
    changed_config = Config(roots=("src/example/orders",), tests=())
    initial_tree = discover_files(config=initial_config, repo_root=tmp_path)
    _CALLS.clear()
    project_rule = _spec(_project_position)
    _ = evaluate_with_cache(
        tree=initial_tree,
        ruleset=(project_rule,),
        config=initial_config,
        global_fingerprint=_FINGERPRINT,
    )
    changed_tree = discover_files(config=changed_config, repo_root=tmp_path)

    changed = evaluate_with_cache(
        tree=changed_tree,
        ruleset=(project_rule,),
        config=changed_config,
        global_fingerprint=_FINGERPRINT,
    )

    assert changed.stats.invalidations == 1
    assert _CALLS == {"position": 2}


def test_given_project_surface_is_stored_when_replaying_then_short_circuit_is_exact(
    tmp_path: Path,
) -> None:
    (tmp_path / "src/example").mkdir(parents=True)
    config = Config(roots=("src/example",), tests=())
    tree = discover_files(config=config, repo_root=tmp_path)
    project_rule = _spec(_project_files)
    cold = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    assert cold.surface_targets == (".",)
    assert cold.surface_index_fingerprint is not None
    cache = ResultCache(repo_root=tmp_path)
    assert cache.store_check_output(
        global_fingerprint=_FINGERPRINT,
        targets=cold.surface_targets,
        plain_output="project output\n",
        color_output="\x1b[31mproject output\x1b[0m\n",
        exit_code=1,
        expected_index_fingerprint=cold.surface_index_fingerprint,
    )

    replayed = evaluate_with_cache(
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


def test_given_file_and_project_subjects_when_cached_then_records_replay_separately(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/example/orders/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    config = Config(
        roots=("src/example",),
        tests=(),
        evaluation=EvaluationConfig(include=("src/example/orders/models.py",)),
    )
    tree = discover_files(config=config, repo_root=tmp_path)
    _CALLS.clear()
    rules = (_spec(_file_position), _spec(_project_children))

    cold = evaluate_with_cache(
        tree=tree, ruleset=rules, config=config, global_fingerprint=_FINGERPRINT
    )
    warm = evaluate_with_cache(
        tree=tree, ruleset=rules, config=config, global_fingerprint=_FINGERPRINT
    )

    assert cold.stats.misses == 2
    assert warm.stats.hits == 2
    assert _CALLS == {"src/example/orders/models.py": 1, "children": 1}
    assert _result(cold) == _result(warm)
    assert len(_result(warm).file_evaluations) == 1
    assert _result(warm).project_evaluation is not None


def test_given_nested_target_tree_query_when_replaying_then_prefix_and_narrowness_are_preserved(
    tmp_path: Path,
) -> None:
    model = tmp_path / "apps/service/src/example/orders/models.py"
    support = tmp_path / "apps/service/src/example/support/helpers.py"
    model.parent.mkdir(parents=True)
    support.parent.mkdir(parents=True)
    model.write_text("", encoding="utf-8")
    support.write_text("", encoding="utf-8")
    config = Config(target_root="apps/service", roots=("src/example",), tests=())
    initial_tree = discover_files(config=config, repo_root=tmp_path)
    _CALLS.clear()
    project_rule = _spec(_project_children)
    cold = evaluate_with_cache(
        tree=initial_tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm = evaluate_with_cache(
        tree=initial_tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    (support.parent / "extra.py").write_text("", encoding="utf-8")
    unrelated_tree = discover_files(config=config, repo_root=tmp_path)
    unrelated = evaluate_with_cache(
        tree=unrelated_tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    (model.parent / "service.py").write_text("", encoding="utf-8")
    relevant_tree = discover_files(config=config, repo_root=tmp_path)
    relevant = evaluate_with_cache(
        tree=relevant_tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert cold.stats.misses == 1
    assert warm.stats.hits == 1
    assert unrelated.stats.hits == 1
    assert relevant.stats.invalidations == 1
    assert _result(cold) == _result(warm)
    assert _result(cold).faults == _result(unrelated).faults
    assert _result(cold).project_evaluation == _result(unrelated).project_evaluation
    assert _CALLS == {"children": 2}


def test_given_project_source_location_and_symbol_exception_when_cached_then_replay_matches(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/example/orders/service.py"
    source.parent.mkdir(parents=True)
    source.write_text("def process() -> None:\n    return None\n", encoding="utf-8")
    config = Config(
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
    tree = discover_files(config=config, repo_root=tmp_path)
    project_rule = _spec(_project_location)

    cold = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert cold.stats.misses == 1
    assert warm.stats.hits == 1
    assert _result(cold) == _result(warm)
    assert _result(warm).faults == ()
    assert _result(warm).applied_exception_count == 1


def test_given_symbol_exception_source_moves_when_replaying_then_suppression_invalidates(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/example/orders/service.py"
    source.parent.mkdir(parents=True)
    source.write_text("def process() -> None:\n    return None\n", encoding="utf-8")

    @rule(code="XPC013", family=Family.CUSTOM, slug="symbol-position", message="symbol position")
    def symbol_position(*, project: Project, ctx: RuleContext) -> list[Fault]:
        del project
        _ = ctx.project.tree.files
        return [ctx.fault_for(path=source, line=1, column=0)]

    config = Config(
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
    project_rule = _spec(symbol_position)
    cold = evaluate_with_cache(
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

    assert cold.stats.misses == 1
    assert _result(cold).faults == ()


def test_given_nested_project_symbol_exception_when_evaluating_then_matches_target_relative_path(
    tmp_path: Path,
) -> None:
    source = tmp_path / "apps/service/src/example/orders/service.py"
    source.parent.mkdir(parents=True)
    source.write_text("def process() -> None:\n    return None\n", encoding="utf-8")
    config = Config(
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
    tree = discover_files(config=config, repo_root=tmp_path)

    result = evaluate_with_cache(
        tree=tree,
        ruleset=(_spec(_project_location),),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert _result(result).faults == ()
    assert _result(result).applied_exception_count == 1


def test_given_filtered_files_and_stale_project_exception_when_evaluating_then_reports_stale(
    tmp_path: Path,
) -> None:
    selected = tmp_path / "src/example/selected.py"
    excluded = tmp_path / "src/example/excluded.py"
    selected.parent.mkdir(parents=True)
    selected.write_text("", encoding="utf-8")
    excluded.write_text("", encoding="utf-8")
    config = Config(
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
    tree = discover_files(config=config, repo_root=tmp_path)

    with pytest.raises(ConfigError, match="Stale rule exception"):
        evaluate_with_cache(
            tree=tree,
            ruleset=(_spec(_quiet_project),),
            config=config,
            global_fingerprint=_FINGERPRINT,
        )


def test_given_project_threshold_override_when_cached_then_use_replays_exactly(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/example/orders/service.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    config = Config(
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
    tree = discover_files(config=config, repo_root=tmp_path)
    project_rule = _spec(_project_threshold)

    cold = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    warm = evaluate_with_cache(
        tree=tree,
        ruleset=(project_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert warm.stats.hits == 1
    assert _result(cold) == _result(warm)
    assert _result(warm).faults[0].message == "7"
    assert len(_result(warm).threshold_override_uses) == 1


def test_given_warm_core_only_result_when_replaying_then_project_tree_is_not_built(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/example/orders/service.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    config = Config(roots=("src/example",), tests=())
    tree = discover_files(config=config, repo_root=tmp_path)
    core_rule = source_fault_rule()
    _ = evaluate_with_cache(
        tree=tree,
        ruleset=(core_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )
    import fensu.evaluation.main.build_project as build_project_module

    def fail_build_project(**_: object) -> object:
        raise AssertionError("warm core-only replay built project analysis")

    monkeypatch.setattr(build_project_module, "build_evaluation_project", fail_build_project)

    warm = evaluate_with_cache(
        tree=tree,
        ruleset=(core_rule,),
        config=config,
        global_fingerprint=_FINGERPRINT,
    )

    assert warm.stats.hits == 1
