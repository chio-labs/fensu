"""Coordinate native cache planning with fresh Python rule evaluation."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

from fensu.cache.fingerprints.main._source import fingerprint_source
from fensu.cache.fingerprints.models import CacheFingerprint
from fensu.cache.results._helpers.paths import relative_repository_path
from fensu.cache.results.classes.result_cache import ResultCache
from fensu.cache.results.constants import (
    NATIVE_COLD_MODE,
    NATIVE_EDIT_MODE,
    PROJECT_SUBJECT_IDENTITY,
)
from fensu.cache.results.models import (
    CachedCheckOutput,
    CachedEvaluationSetup,
    CacheEvaluation,
    CacheIndexEntry,
    CacheStats,
    NativeGenerationPlan,
    RuleScopes,
    SubjectRulePartitions,
)
from fensu.cache.storage.exceptions import CachePathError, CacheRecordError
from fensu.discovery.constants import SNAPSHOT_TABLE
from fensu.discovery.main.prime_snapshot_hashes import prime_snapshot_hashes
from fensu.evaluation.exceptions import ProjectAnalysisUnavailableError
from fensu.evaluation.main.build_targets import build_evaluation_targets
from fensu.evaluation.main.select_files import select_evaluation_files
from fensu.instrumentation.constants import CACHE_MANIFEST_VALIDATION_OPERATION, OPERATION_COUNTERS
from fensu.rules.authoring.types import RuleKind

if TYPE_CHECKING:
    from fensu.analysis.models import ProjectDependency
    from fensu.config.models import Config
    from fensu.discovery.models import DiscoveredTree, RepoRoot
    from fensu.evaluation.models import (
        EvaluationResult,
        EvaluationSelection,
        EvaluationTarget,
        FileEvaluation,
        ProjectEvaluation,
    )
    from fensu.evaluation.types import EvaluationProjectAnalysis
    from fensu.rules.authoring.models import CustomRuleRegistration, RuleSpec


def run_cached_evaluation(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...] = (),
    config: Config,
    global_fingerprint: CacheFingerprint,
    custom_rule_registrations: tuple[CustomRuleRegistration, ...] = (),
    allow_short_circuit: bool = True,
    cache_storage_root: Path | None = None,
    jobs: int = 1,
) -> CacheEvaluation:
    """Return a complete evaluation using only native-validated cache hits."""

    setup: CachedEvaluationSetup = _prepare_cached_evaluation(
        tree=tree,
        ruleset=ruleset,
        warning_rules=warning_rules,
        config=config,
        custom_rule_registrations=custom_rule_registrations,
    )
    partitions: SubjectRulePartitions = setup.partitions
    selection: EvaluationSelection = setup.selection
    targets: tuple[EvaluationTarget, ...] = setup.targets
    scopes: RuleScopes = setup.file_scopes
    project_scopes: RuleScopes = setup.project_scopes
    if not (
        scopes.cacheable_ruleset
        or scopes.cacheable_warning_rules
        or project_scopes.cacheable_ruleset
        or project_scopes.cacheable_warning_rules
    ):
        from fensu.evaluation.main.evaluate import evaluate

        result: EvaluationResult = evaluate(
            tree=tree,
            ruleset=ruleset,
            warning_rules=warning_rules,
            config=config,
            custom_rule_registrations=custom_rule_registrations,
        )
        return CacheEvaluation(
            result=result,
            stats=CacheStats(
                non_cacheable=len(targets)
                + int(bool(partitions.project_rules or partitions.project_warnings))
            ),
        )
    cache: ResultCache = ResultCache(
        repo_root=tree.repo_root.path,
        storage_root=cache_storage_root,
    )
    target_paths, source_fingerprints = _target_source_state(
        targets=targets,
        repo_root=tree.repo_root.path,
    )
    has_cached_project: bool = bool(
        project_scopes.cacheable_ruleset or project_scopes.cacheable_warning_rules
    )
    sorted_targets: tuple[str, ...] = (
        *tuple(sorted(target_paths)),
        *((PROJECT_SUBJECT_IDENTITY,) if has_cached_project else ()),
    )
    if has_cached_project:
        source_fingerprints[PROJECT_SUBJECT_IDENTITY] = CacheFingerprint("0" * 64)
    cacheable_rules: tuple[RuleSpec, ...] = (
        *scopes.cacheable_ruleset,
        *scopes.cacheable_warning_rules,
        *project_scopes.cacheable_ruleset,
        *project_scopes.cacheable_warning_rules,
    )
    dependency_kinds: frozenset[str] | None = (
        cache.native_dependency_kinds(
            global_fingerprint=global_fingerprint,
            targets=sorted_targets,
            source_fingerprints=source_fingerprints,
            project_subject=has_cached_project,
        )
        if any(rule.kind is RuleKind.CUSTOM for rule in cacheable_rules)
        else frozenset()
    )
    needs_tree_snapshot: bool = dependency_kinds is not None and any(
        kind.startswith("tree_") for kind in dependency_kinds
    )
    needs_graph_snapshot: bool = dependency_kinds is not None and any(
        kind.startswith("graph_") for kind in dependency_kinds
    )
    project: EvaluationProjectAnalysis | None = None
    tree_snapshot: dict[str, object] | None = None
    if needs_tree_snapshot or needs_graph_snapshot:
        from fensu.evaluation.main.build_project import build_evaluation_project
        from fensu.rules.authoring.main.project_tree_snapshot import project_tree_snapshot

        project = build_evaluation_project(tree=tree)
        tree_snapshot = (
            project_tree_snapshot(tree=project.project_tree) if needs_tree_snapshot else {}
        )
        if needs_graph_snapshot:
            tree_snapshot["graph"] = project.graph_snapshot()
    replayed: CacheEvaluation | None = _native_replayed_evaluation(
        cache=cache,
        scopes=scopes,
        allow_short_circuit=allow_short_circuit and not project_scopes.scoped,
        global_fingerprint=global_fingerprint,
        targets=targets,
        sorted_targets=sorted_targets,
        source_fingerprints=source_fingerprints,
        project_subject=has_cached_project,
        tree_snapshot=tree_snapshot,
    )
    if replayed is not None:
        return replayed
    targets = (
        build_evaluation_targets(
            tree=tree,
            selection=selection,
            ruleset=partitions.file_rules,
            warning_rules=partitions.file_warnings,
            custom_rule_registrations=custom_rule_registrations,
        )
        if partitions.file_rules or partitions.file_warnings
        else ()
    )
    plan: NativeGenerationPlan | None = cache.plan_native_generation(
        global_fingerprint=global_fingerprint,
        targets=sorted_targets,
        source_fingerprints=source_fingerprints,
        allow_edit=not scopes.scoped and not project_scopes.scoped and not has_cached_project,
        project_subject=has_cached_project,
        tree_snapshot=tree_snapshot,
    )
    if plan is None:
        return _failed_cache_evaluation(
            tree=tree,
            ruleset=ruleset,
            warning_rules=warning_rules,
            config=config,
            custom_rule_registrations=custom_rule_registrations,
            target_count=len(sorted_targets),
        )
    if plan.mode == NATIVE_COLD_MODE and jobs > 1 and not scopes.scoped and not has_cached_project:
        return _parallel_cold_cache_evaluation(
            cache=cache,
            tree=tree,
            config=config,
            ruleset=ruleset,
            warning_rules=warning_rules,
            custom_rule_registrations=custom_rule_registrations,
            global_fingerprint=global_fingerprint,
            targets=targets,
            sorted_targets=sorted_targets,
            jobs=jobs,
        )
    needs_project: bool = bool(plan.miss_paths or scopes.scoped or project_scopes.scoped)
    if project is None and needs_project:
        from fensu.evaluation.main.build_project import build_evaluation_project

        project = build_evaluation_project(tree=tree)
    file_misses: frozenset[str] = frozenset(plan.miss_paths).intersection(target_paths)
    fresh: tuple[FileEvaluation, ...] = (
        _evaluate_misses(
            plan=plan,
            targets=targets,
            scopes=scopes,
            config=config,
            tree=tree,
            project=_required_project(project),
        )
        if file_misses
        else ()
    )
    evaluations: tuple[FileEvaluation, ...] = _planned_evaluations(
        plan=plan,
        fresh=fresh,
        targets=targets,
        repo_root=tree.repo_root.path,
    )
    if scopes.scoped:
        evaluations = tuple(
            _supplemented(
                evaluation=evaluation,
                target=target,
                fresh_ruleset=scopes.fresh_ruleset,
                fresh_warning_rules=scopes.fresh_warning_rules,
                config=config,
                tree=tree,
                project=_required_project(project),
            )
            for target, evaluation in zip(targets, evaluations, strict=True)
        )
    from fensu.evaluation.main.evaluate_project_rules import evaluate_project_rules

    project_evaluation: ProjectEvaluation | None = plan.cached_project_evaluation
    fresh_project: ProjectEvaluation | None = None
    if has_cached_project and PROJECT_SUBJECT_IDENTITY in plan.miss_paths:
        fresh_project = evaluate_project_rules(
            ruleset=project_scopes.cacheable_ruleset,
            warning_rules=project_scopes.cacheable_warning_rules,
            config=config,
            tree=tree,
            analysis=_required_project(project),
        )
        project_evaluation = fresh_project
    if project_scopes.scoped:
        supplement: ProjectEvaluation | None = evaluate_project_rules(
            ruleset=project_scopes.fresh_ruleset,
            warning_rules=project_scopes.fresh_warning_rules,
            config=config,
            tree=tree,
            analysis=_required_project(project),
        )
        project_evaluation = _merge_project_evaluations(first=project_evaluation, second=supplement)
    dependencies: list[ProjectDependency] = []
    for evaluation in evaluations:
        dependencies.extend(evaluation.dependencies)
    if project_evaluation is not None:
        dependencies.extend(project_evaluation.dependencies)
    from fensu.evaluation.main.collect_result import collect_file_evaluations

    project_root: RepoRoot = tree.repo_root if tree.project_root is None else tree.project_root
    result: EvaluationResult = collect_file_evaluations(
        file_evaluations=evaluations,
        dependencies=tuple(dependencies),
        config=config,
        repo_root=tree.repo_root.path,
        project_root=project_root.path,
        evaluated_rule_codes=frozenset(rule.code for rule in (*ruleset, *warning_rules)),
        project_rule_codes=frozenset(
            rule.code for rule in (*partitions.project_rules, *partitions.project_warnings)
        ),
        selection=selection,
        project_evaluation=project_evaluation,
    )
    publication: CacheStats = (
        _publish_native_generation(
            cache=cache,
            global_fingerprint=global_fingerprint,
            evaluations=(*fresh, *((fresh_project,) if fresh_project is not None else ())),
            retained_entries=plan.retained_entries,
            expected_index_fingerprint=plan.index_fingerprint,
            retain_all_observations=(plan.mode == NATIVE_EDIT_MODE and bool(plan.retained_entries)),
        )
        if plan.miss_paths or plan.invalidations
        else CacheStats(index_fingerprint=plan.index_fingerprint)
    )
    surface_ready: bool = (
        not scopes.scoped
        and not project_scopes.scoped
        and publication.non_cacheable == 0
        and not publication.storage_failed
        and not publication.internal_error
        and publication.index_fingerprint is not None
    )
    return CacheEvaluation(
        result=result,
        stats=CacheStats(
            hits=plan.hits,
            misses=plan.misses,
            invalidations=plan.invalidations,
            writes=publication.writes,
            non_cacheable=(
                publication.non_cacheable
                + (len(targets) if scopes.scoped else 0)
                + int(project_scopes.scoped)
            ),
            storage_failed=publication.storage_failed,
            internal_error=publication.internal_error,
        ),
        surface_targets=sorted_targets if surface_ready else None,
        surface_index_fingerprint=publication.index_fingerprint if surface_ready else None,
    )


def _failed_cache_evaluation(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
    config: Config,
    custom_rule_registrations: tuple[CustomRuleRegistration, ...],
    target_count: int,
) -> CacheEvaluation:
    from fensu.evaluation.main.evaluate import evaluate

    result: EvaluationResult = evaluate(
        tree=tree,
        ruleset=ruleset,
        warning_rules=warning_rules,
        config=config,
        custom_rule_registrations=custom_rule_registrations,
    )
    return CacheEvaluation(
        result=result,
        stats=CacheStats(misses=target_count, storage_failed=True),
    )


def _evaluate_misses(
    *,
    plan: NativeGenerationPlan,
    targets: tuple[EvaluationTarget, ...],
    scopes: RuleScopes,
    config: Config,
    tree: DiscoveredTree,
    project: EvaluationProjectAnalysis,
) -> tuple[FileEvaluation, ...]:
    from fensu.evaluation.main.evaluate_target_chunk import evaluate_target_chunk

    ordered_paths: list[str] = [
        target.scoped_file.path.relative_to(tree.repo_root.path).as_posix() for target in targets
    ]
    native: ModuleType = import_module("fensu._native")
    work_indexes: list[int] = native.partition_native_execution_targets(
        ordered_paths,
        list(plan.miss_paths),
    )
    miss_targets: tuple[EvaluationTarget, ...] = tuple(targets[index] for index in work_indexes)
    return evaluate_target_chunk(
        targets=miss_targets,
        ruleset=scopes.cacheable_ruleset,
        warning_rules=scopes.cacheable_warning_rules,
        config=config,
        tree=tree,
        project=project,
    )


def _planned_evaluations(
    *,
    plan: NativeGenerationPlan,
    fresh: tuple[FileEvaluation, ...],
    targets: tuple[EvaluationTarget, ...],
    repo_root: Path,
) -> tuple[FileEvaluation, ...]:
    retained: tuple[FileEvaluation, ...] = (
        plan.retained_evaluations if plan.mode == NATIVE_EDIT_MODE else plan.cached_evaluations
    )
    by_path: dict[str, FileEvaluation] = {
        evaluation.path.relative_to(repo_root).as_posix(): evaluation
        for evaluation in (*retained, *fresh)
    }
    ordered: list[FileEvaluation] = []
    for target in targets:
        path: str | None = relative_repository_path(
            path=target.scoped_file.path,
            repo_root=repo_root,
        )
        if path is not None and path in by_path:
            ordered.append(by_path[path])
    return tuple(ordered)


def _native_replayed_evaluation(
    *,
    cache: ResultCache,
    scopes: RuleScopes,
    allow_short_circuit: bool,
    global_fingerprint: CacheFingerprint,
    targets: tuple[EvaluationTarget, ...],
    sorted_targets: tuple[str, ...],
    source_fingerprints: dict[str, CacheFingerprint | None],
    project_subject: bool,
    tree_snapshot: dict[str, object] | None,
) -> CacheEvaluation | None:
    if not allow_short_circuit or scopes.scoped:
        return None
    OPERATION_COUNTERS.record(operation=CACHE_MANIFEST_VALIDATION_OPERATION)
    output: CachedCheckOutput | None = cache.load_native_replay(
        global_fingerprint=global_fingerprint,
        targets=sorted_targets,
        source_fingerprints=source_fingerprints,
        project_subject=project_subject,
        tree_snapshot=tree_snapshot,
    )
    if output is None:
        return None
    return CacheEvaluation(
        result=None,
        stats=CacheStats(hits=len(sorted_targets)),
        short_circuit=output,
    )


def _parallel_cold_cache_evaluation(
    *,
    cache: ResultCache,
    tree: DiscoveredTree,
    config: Config,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
    custom_rule_registrations: tuple[CustomRuleRegistration, ...],
    global_fingerprint: CacheFingerprint,
    targets: tuple[EvaluationTarget, ...],
    sorted_targets: tuple[str, ...],
    jobs: int,
) -> CacheEvaluation:
    from fensu.evaluation.main.evaluate_parallel import evaluate_parallel

    result: EvaluationResult = evaluate_parallel(
        tree=tree,
        config=config,
        ruleset=ruleset,
        warning_rules=warning_rules,
        custom_rule_registrations=custom_rule_registrations,
        jobs=jobs,
    )
    publication: CacheStats = _publish_native_generation(
        cache=cache,
        global_fingerprint=global_fingerprint,
        evaluations=result.file_evaluations,
        retained_entries=(),
        expected_index_fingerprint=None,
        retain_all_observations=False,
    )
    surface_ready: bool = (
        publication.non_cacheable == 0
        and not publication.storage_failed
        and not publication.internal_error
        and publication.index_fingerprint is not None
    )
    return CacheEvaluation(
        result=result,
        stats=CacheStats(
            misses=len(targets),
            writes=publication.writes,
            non_cacheable=publication.non_cacheable,
            storage_failed=publication.storage_failed,
            internal_error=publication.internal_error,
        ),
        surface_targets=sorted_targets if surface_ready else None,
        surface_index_fingerprint=publication.index_fingerprint if surface_ready else None,
    )


def _rule_scopes(
    *,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
) -> RuleScopes:
    fresh_ruleset: tuple[RuleSpec, ...] = _fresh_subset(ruleset)
    fresh_warning_rules: tuple[RuleSpec, ...] = _fresh_subset(warning_rules)
    return RuleScopes(
        fresh_ruleset=fresh_ruleset,
        fresh_warning_rules=fresh_warning_rules,
        cacheable_ruleset=_cacheable_subset(ruleset),
        cacheable_warning_rules=_cacheable_subset(warning_rules),
        scoped=bool(fresh_ruleset or fresh_warning_rules),
        fully_fresh=(
            len(fresh_ruleset) == len(ruleset) and len(fresh_warning_rules) == len(warning_rules)
        ),
    )


def _fresh_subset(rules: tuple[RuleSpec, ...]) -> tuple[RuleSpec, ...]:
    return tuple(rule for rule in rules if rule.kind is RuleKind.CUSTOM and not rule.cacheable)


def _cacheable_subset(rules: tuple[RuleSpec, ...]) -> tuple[RuleSpec, ...]:
    return tuple(rule for rule in rules if rule.kind is not RuleKind.CUSTOM or rule.cacheable)


def _supplemented(
    *,
    evaluation: FileEvaluation,
    target: EvaluationTarget,
    fresh_ruleset: tuple[RuleSpec, ...],
    fresh_warning_rules: tuple[RuleSpec, ...],
    config: Config,
    tree: DiscoveredTree,
    project: EvaluationProjectAnalysis,
) -> FileEvaluation:
    from fensu.evaluation.main.evaluate_target import evaluate_target
    from fensu.evaluation.main.merge_evaluations import merge_file_evaluations
    from fensu.evaluation.models import EvaluationTarget

    if not target.direct:
        return evaluation
    fresh: FileEvaluation = evaluate_target(
        target=EvaluationTarget(
            scoped_file=target.scoped_file,
            direct=True,
            applicable_rule_codes=target.applicable_rule_codes,
        ),
        ruleset=fresh_ruleset,
        warning_rules=fresh_warning_rules,
        config=config,
        tree=tree,
        project=project,
    )
    return merge_file_evaluations(evaluations=(evaluation, fresh))


def _publish_native_generation(
    *,
    cache: ResultCache,
    global_fingerprint: CacheFingerprint,
    evaluations: tuple[FileEvaluation | ProjectEvaluation, ...],
    retained_entries: tuple[CacheIndexEntry, ...],
    expected_index_fingerprint: CacheFingerprint | None,
    retain_all_observations: bool,
) -> CacheStats:
    try:
        return cache.publish_native_generation(
            global_fingerprint=global_fingerprint,
            evaluations=evaluations,
            retained_entries=retained_entries,
            expected_index_fingerprint=expected_index_fingerprint,
            retain_all_observations=retain_all_observations,
        )
    except (CachePathError, CacheRecordError, TypeError, ValueError):
        return CacheStats(storage_failed=True, internal_error=True)


def _merge_project_evaluations(
    *, first: ProjectEvaluation | None, second: ProjectEvaluation | None
) -> ProjectEvaluation | None:
    if first is None:
        return second
    if second is None:
        return first
    return ProjectEvaluation(
        faults=(*first.faults, *second.faults),
        warnings=(*first.warnings, *second.warnings),
        applied_exception_keys=tuple(
            sorted(
                {*first.applied_exception_keys, *second.applied_exception_keys},
                key=lambda key: (key.rule, key.path, key.symbol or ""),
            )
        ),
        dependencies=(*first.dependencies, *second.dependencies),
        threshold_override_uses=(
            *first.threshold_override_uses,
            *second.threshold_override_uses,
        ),
    )


def _required_project(
    project: EvaluationProjectAnalysis | None,
) -> EvaluationProjectAnalysis:
    if project is None:
        raise ProjectAnalysisUnavailableError(
            "project analysis was not prepared for fresh rule evaluation"
        )
    return project


def _prepare_cached_evaluation(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
    config: Config,
    custom_rule_registrations: tuple[CustomRuleRegistration, ...],
) -> CachedEvaluationSetup:
    """Prepare subject partitions, selected files, targets, and cache scopes."""

    partitions: SubjectRulePartitions = _partition_subject_rules(
        ruleset=ruleset, warning_rules=warning_rules
    )
    selection: EvaluationSelection = select_evaluation_files(
        tree=tree, config=config.evaluation, allow_empty=config.dead_code.enabled
    )
    targets: tuple[EvaluationTarget, ...] = (
        build_evaluation_targets(
            tree=tree,
            selection=selection,
            ruleset=partitions.file_rules,
            warning_rules=partitions.file_warnings,
            custom_rule_registrations=custom_rule_registrations,
            plan_rule_owners=False,
        )
        if partitions.file_rules or partitions.file_warnings
        else ()
    )
    return CachedEvaluationSetup(
        partitions=partitions,
        selection=selection,
        targets=targets,
        file_scopes=_rule_scopes(
            ruleset=partitions.file_rules,
            warning_rules=partitions.file_warnings,
        ),
        project_scopes=_rule_scopes(
            ruleset=partitions.project_rules,
            warning_rules=partitions.project_warnings,
        ),
    )


def _partition_subject_rules(
    *, ruleset: tuple[RuleSpec, ...], warning_rules: tuple[RuleSpec, ...]
) -> SubjectRulePartitions:
    """Partition file and project rules while preserving authored order."""

    from fensu.rules.authoring.types import RuleSubjectKind

    file_rules: tuple[RuleSpec, ...] = tuple(
        rule for rule in ruleset if rule.subject_kind is not RuleSubjectKind.PROJECT
    )
    file_warnings: tuple[RuleSpec, ...] = tuple(
        rule for rule in warning_rules if rule.subject_kind is not RuleSubjectKind.PROJECT
    )
    project_rules: tuple[RuleSpec, ...] = tuple(
        rule for rule in ruleset if rule.subject_kind is RuleSubjectKind.PROJECT
    )
    project_warnings: tuple[RuleSpec, ...] = tuple(
        rule for rule in warning_rules if rule.subject_kind is RuleSubjectKind.PROJECT
    )
    return SubjectRulePartitions(
        file_rules=file_rules,
        file_warnings=file_warnings,
        project_rules=project_rules,
        project_warnings=project_warnings,
    )


def _target_source_state(
    *,
    targets: tuple[EvaluationTarget, ...],
    repo_root: Path,
) -> tuple[set[str], dict[str, CacheFingerprint | None]]:
    prime_snapshot_hashes(paths=tuple(target.scoped_file.path for target in targets))
    target_paths: set[str] = set()
    source_fingerprints: dict[str, CacheFingerprint | None] = {}
    for target in targets:
        discovered_path: str | None = relative_repository_path(
            path=target.scoped_file.path,
            repo_root=repo_root,
        )
        if discovered_path is not None:
            target_paths.add(discovered_path)
            source_fingerprints[discovered_path] = _source_fingerprint(target.scoped_file.path)
    return target_paths, source_fingerprints


def _source_fingerprint(path: Path) -> CacheFingerprint | None:
    snapshot_hash: str | None = SNAPSHOT_TABLE.source_hash(path=path)
    if snapshot_hash is not None:
        return CacheFingerprint(value=snapshot_hash)
    try:
        return fingerprint_source(path.read_bytes())
    except OSError:
        return None
