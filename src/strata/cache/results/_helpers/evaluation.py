"""Coordinate cached and fresh per-file evaluation results."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from strata.cache.fingerprints.main.source import fingerprint_source
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results._helpers.dependencies import dependencies_are_current
from strata.cache.results._helpers.paths import relative_repository_path
from strata.cache.results.classes.result_cache import ResultCache
from strata.cache.results.models import (
    CachedCheckOutput,
    CachedCollectionContribution,
    CachedFileResult,
    CacheEvaluation,
    CacheIndex,
    CacheIndexEntry,
    CacheLookup,
    CacheStats,
    CheckCacheContext,
    DependencyObservation,
    EditReplaySurface,
)
from strata.cache.results.types import DependencyStateCache
from strata.cache.storage.exceptions import CachePathError, CacheRecordError
from strata.discovery.constants import SNAPSHOT_TABLE
from strata.discovery.main.prime_snapshot_hashes import prime_snapshot_hashes
from strata.evaluation.constants import PREWARM_CHUNK_SIZE
from strata.evaluation.main.build_targets import build_evaluation_targets
from strata.evaluation.main.select_files import select_evaluation_files
from strata.instrumentation.constants import CACHE_MANIFEST_VALIDATION_OPERATION, OPERATION_COUNTERS
from strata.rules.authoring.types import RuleKind

if TYPE_CHECKING:
    from strata.analysis.models import ProjectDependency
    from strata.config.models import Config
    from strata.discovery.models import DiscoveredTree
    from strata.evaluation.models import (
        EvaluationResult,
        EvaluationSelection,
        EvaluationTarget,
        FileEvaluation,
    )
    from strata.evaluation.types import EvaluationProjectAnalysis
    from strata.rules.authoring.models import CustomRuleRegistration, RuleSpec


@dataclass(frozen=True, slots=True)
class _EditReplayInputs:
    """Validated inputs shared by one edit-replay qualification attempt."""

    scopes: _RuleScopes
    context: CheckCacheContext
    entries: dict[str, CacheIndexEntry]
    targets: tuple[EvaluationTarget, ...]
    sorted_targets: tuple[str, ...]
    source_fingerprints: dict[str, CacheFingerprint | None]
    selection: EvaluationSelection
    config: Config
    tree: DiscoveredTree
    states: DependencyStateCache
    global_fingerprint: CacheFingerprint
    evaluated_rules: tuple[RuleSpec, ...]
    custom_rule_registrations: tuple[CustomRuleRegistration, ...]


@dataclass(frozen=True, slots=True)
class _TargetDecision:
    """One target's cache lookup outcome ahead of fresh evaluation."""

    target: EvaluationTarget
    entry: CacheIndexEntry | None
    lookup: CacheLookup | None


@dataclass(frozen=True, slots=True)
class _RuleScopes:
    """The cacheable and per-run-fresh partitions of the evaluated rules."""

    fresh_ruleset: tuple[RuleSpec, ...]
    fresh_warning_rules: tuple[RuleSpec, ...]
    cacheable_ruleset: tuple[RuleSpec, ...]
    cacheable_warning_rules: tuple[RuleSpec, ...]
    scoped: bool
    fully_fresh: bool


def run_cached_evaluation(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...] = (),
    config: Config,
    global_fingerprint: CacheFingerprint,
    custom_rule_registrations: tuple[CustomRuleRegistration, ...] = (),
    allow_short_circuit: bool = True,
    jobs: int = 1,
) -> CacheEvaluation:
    """Return a complete evaluation using only fully validated file-result hits."""

    selection: EvaluationSelection = select_evaluation_files(tree=tree, config=config.evaluation)
    evaluated_rules: tuple[RuleSpec, ...] = (*ruleset, *warning_rules)
    targets: tuple[EvaluationTarget, ...] = build_evaluation_targets(
        tree=tree,
        selection=selection,
        ruleset=ruleset,
        warning_rules=warning_rules,
        custom_rule_registrations=custom_rule_registrations,
    )
    scopes: _RuleScopes = _rule_scopes(ruleset=ruleset, warning_rules=warning_rules)
    if scopes.fully_fresh:
        from strata.evaluation.main.evaluate import evaluate

        result: EvaluationResult = evaluate(
            tree=tree,
            ruleset=ruleset,
            warning_rules=warning_rules,
            config=config,
            custom_rule_registrations=custom_rule_registrations,
        )
        return CacheEvaluation(
            result=result,
            stats=CacheStats(non_cacheable=len(targets)),
        )
    cache: ResultCache = ResultCache(repo_root=tree.repo_root.path)
    target_paths, source_fingerprints = _target_source_state(
        targets=targets,
        repo_root=tree.repo_root.path,
    )
    sorted_targets: tuple[str, ...] = tuple(sorted(target_paths))
    native_replay: CacheEvaluation | None = _native_replayed_evaluation(
        cache=cache,
        scopes=scopes,
        allow_short_circuit=allow_short_circuit,
        global_fingerprint=global_fingerprint,
        targets=targets,
        sorted_targets=sorted_targets,
        source_fingerprints=source_fingerprints,
    )
    if native_replay is not None:
        return native_replay
    context, entries = _loaded_cache_context(
        cache=cache,
        global_fingerprint=global_fingerprint,
    )
    replay_inputs: _EditReplayInputs = _EditReplayInputs(
        scopes=scopes,
        context=context,
        entries=entries,
        targets=targets,
        sorted_targets=sorted_targets,
        source_fingerprints=source_fingerprints,
        selection=selection,
        config=config,
        tree=tree,
        states={},
        global_fingerprint=global_fingerprint,
        evaluated_rules=evaluated_rules,
        custom_rule_registrations=custom_rule_registrations,
    )
    early: CacheEvaluation | None = _early_cached_evaluation(
        cache=cache,
        inputs=replay_inputs,
        allow_short_circuit=allow_short_circuit,
        jobs=jobs,
        ruleset=ruleset,
        warning_rules=warning_rules,
    )
    if early is not None:
        return early
    from strata.evaluation.main.build_project import build_evaluation_project
    from strata.evaluation.main.evaluate_target_chunk import evaluate_target_chunk

    loaded_entries: tuple[CacheIndexEntry, ...] = tuple(
        entry
        for path, entry in entries.items()
        if path in target_paths and source_fingerprints.get(path) == entry.source_fingerprint
    )
    loaded_results: dict[str, CachedFileResult | None] = cache.load_results(
        global_fingerprint=global_fingerprint,
        entries=loaded_entries,
        dependency_fingerprint=(
            context.index.dependencies_fingerprint if context.index is not None else None
        ),
    )
    project: EvaluationProjectAnalysis = build_evaluation_project(tree=tree)
    ordered_results: list[FileEvaluation | CachedFileResult] = []
    fresh_evaluations: list[FileEvaluation] = []
    retained_entries: list[CacheIndexEntry] = []
    hits: int = 0
    misses: int = 0
    invalidations: int = sum(path not in target_paths for path in entries)
    decisions: tuple[_TargetDecision, ...] = _target_decisions(
        targets=targets,
        tree=tree,
        cache=cache,
        entries=entries,
        source_fingerprints=source_fingerprints,
        loaded_results=loaded_results,
        dependency_states=replay_inputs.states,
    )
    miss_targets: tuple[EvaluationTarget, ...] = tuple(
        decision.target
        for decision in decisions
        if decision.lookup is None or decision.lookup.result is None
    )
    evaluated_misses: list[FileEvaluation] = []
    for start in range(0, len(miss_targets), PREWARM_CHUNK_SIZE):
        evaluated_misses.extend(
            evaluate_target_chunk(
                targets=miss_targets[start : start + PREWARM_CHUNK_SIZE],
                ruleset=scopes.cacheable_ruleset,
                warning_rules=scopes.cacheable_warning_rules,
                config=config,
                tree=tree,
                project=project,
            )
        )
    fresh_iterator: Iterator[FileEvaluation] = iter(evaluated_misses)
    for decision in decisions:
        lookup: CacheLookup | None = decision.lookup
        if lookup is not None and lookup.result is not None:
            ordered_results.append(lookup.result)
            hits += 1
            if decision.entry is not None:
                retained_entries.append(decision.entry)
            continue
        if lookup is None or lookup.missed:
            misses += 1
        else:
            invalidations += 1
        fresh: FileEvaluation = next(fresh_iterator)
        ordered_results.append(fresh)
        fresh_evaluations.append(fresh)
    if (
        allow_short_circuit
        and not scopes.scoped
        and context.output is not None
        and misses == 0
        and invalidations == 0
        and not fresh_evaluations
        and context.output.targets == sorted_targets
    ):
        return CacheEvaluation(
            result=None,
            stats=CacheStats(hits=hits),
            short_circuit=context.output,
        )
    evaluations: tuple[FileEvaluation, ...] = tuple(
        _materialized(item=item, repo_root=tree.repo_root.path) for item in ordered_results
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
                project=project,
            )
            for target, evaluation in zip(targets, evaluations, strict=True)
        )
    collected_dependencies: list[ProjectDependency] = []
    for file_evaluation in evaluations:
        collected_dependencies.extend(file_evaluation.dependencies)
    dependencies: tuple[ProjectDependency, ...] = tuple(collected_dependencies)
    from strata.evaluation.main.collect_result import collect_file_evaluations

    result = collect_file_evaluations(
        file_evaluations=evaluations,
        dependencies=dependencies,
        config=config,
        repo_root=tree.repo_root.path,
        evaluated_rule_codes=frozenset(rule.code for rule in evaluated_rules),
        selection=selection,
    )
    retained_results: list[CachedFileResult] = []
    for item in ordered_results:
        if isinstance(item, CachedFileResult):
            retained_results.append(item)
    collection: tuple[CachedCollectionContribution, ...] | None = _slow_path_collection(
        scopes=scopes,
        custom_rule_registrations=custom_rule_registrations,
        evaluations=evaluations,
        repo_root=tree.repo_root.path,
    )
    publication: CacheStats = _publish_results(
        cache=cache,
        global_fingerprint=global_fingerprint,
        fresh_evaluations=tuple(fresh_evaluations),
        retained_entries=tuple(retained_entries),
        retained_results=tuple(retained_results),
        existing_index_fingerprint=context.index_fingerprint,
        collection=collection,
    )
    surface_ready: bool = (
        not scopes.scoped
        and publication.non_cacheable == 0
        and not publication.storage_failed
        and not publication.internal_error
        and publication.index_fingerprint is not None
    )
    return CacheEvaluation(
        result=result,
        stats=CacheStats(
            hits=hits,
            misses=misses,
            invalidations=invalidations,
            writes=publication.writes,
            non_cacheable=publication.non_cacheable,
            storage_failed=publication.storage_failed,
            internal_error=publication.internal_error,
        ),
        surface_targets=sorted_targets if surface_ready else None,
        surface_index_fingerprint=publication.index_fingerprint if surface_ready else None,
    )


def _slow_path_collection(
    *,
    scopes: _RuleScopes,
    custom_rule_registrations: tuple[CustomRuleRegistration, ...],
    evaluations: tuple[FileEvaluation, ...],
    repo_root: Path,
) -> tuple[CachedCollectionContribution, ...] | None:
    if scopes.scoped or custom_rule_registrations:
        return None
    from strata.cache.results._helpers.conversion import build_collection_contributions

    return build_collection_contributions(evaluations=evaluations, repo_root=repo_root)


def _native_replayed_evaluation(
    *,
    cache: ResultCache,
    scopes: _RuleScopes,
    allow_short_circuit: bool,
    global_fingerprint: CacheFingerprint,
    targets: tuple[EvaluationTarget, ...],
    sorted_targets: tuple[str, ...],
    source_fingerprints: dict[str, CacheFingerprint | None],
) -> CacheEvaluation | None:
    if not allow_short_circuit or scopes.scoped:
        return None
    OPERATION_COUNTERS.record(operation=CACHE_MANIFEST_VALIDATION_OPERATION)
    output: CachedCheckOutput | None = cache.load_native_replay(
        global_fingerprint=global_fingerprint,
        targets=sorted_targets,
        source_fingerprints=source_fingerprints,
    )
    if output is None:
        return None
    return CacheEvaluation(
        result=None,
        stats=CacheStats(hits=len(targets)),
        short_circuit=output,
    )


def _loaded_cache_context(
    *,
    cache: ResultCache,
    global_fingerprint: CacheFingerprint,
) -> tuple[CheckCacheContext, dict[str, CacheIndexEntry]]:
    context: CheckCacheContext = cache.load_check_context(global_fingerprint=global_fingerprint)
    index: CacheIndex | None = context.index
    entries: dict[str, CacheIndexEntry] = (
        {entry.path: entry for entry in index.entries} if index is not None else {}
    )
    return context, entries


def _early_cached_evaluation(
    *,
    cache: ResultCache,
    inputs: _EditReplayInputs,
    allow_short_circuit: bool,
    jobs: int,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
) -> CacheEvaluation | None:
    replayed: CacheEvaluation | None = (
        _attempted_replays(cache=cache, inputs=inputs)
        if allow_short_circuit
        else _edit_replayed_evaluation(cache=cache, inputs=inputs)
    )
    if replayed is not None:
        return replayed
    if inputs.entries or jobs <= 1 or inputs.scopes.scoped:
        return None
    return _parallel_cold_cache_evaluation(
        cache=cache,
        tree=inputs.tree,
        config=inputs.config,
        ruleset=ruleset,
        warning_rules=warning_rules,
        custom_rule_registrations=inputs.custom_rule_registrations,
        global_fingerprint=inputs.global_fingerprint,
        targets=inputs.targets,
        sorted_targets=inputs.sorted_targets,
        jobs=jobs,
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
    from strata.evaluation.main.evaluate_parallel import evaluate_parallel

    result: EvaluationResult = evaluate_parallel(
        tree=tree,
        config=config,
        ruleset=ruleset,
        warning_rules=warning_rules,
        custom_rule_registrations=custom_rule_registrations,
        jobs=jobs,
    )
    evaluations: tuple[FileEvaluation, ...] = result.file_evaluations
    collection: tuple[CachedCollectionContribution, ...] | None = _slow_path_collection(
        scopes=_rule_scopes(ruleset=ruleset, warning_rules=warning_rules),
        custom_rule_registrations=custom_rule_registrations,
        evaluations=evaluations,
        repo_root=tree.repo_root.path,
    )
    publication: CacheStats = _publish_results(
        cache=cache,
        global_fingerprint=global_fingerprint,
        fresh_evaluations=evaluations,
        retained_entries=(),
        retained_results=(),
        existing_index_fingerprint=None,
        collection=collection,
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


def _attempted_replays(
    *,
    cache: ResultCache,
    inputs: _EditReplayInputs,
) -> CacheEvaluation | None:
    replayed: CacheEvaluation | None = _replayed_evaluation(
        cache=cache,
        scopes=inputs.scopes,
        context=inputs.context,
        entries=inputs.entries,
        sorted_targets=inputs.sorted_targets,
        source_fingerprints=inputs.source_fingerprints,
        repo_root=inputs.tree.repo_root.path,
        states=inputs.states,
        global_fingerprint=inputs.global_fingerprint,
        target_count=len(inputs.targets),
    )
    if replayed is not None:
        return replayed
    return _edit_replayed_evaluation(cache=cache, inputs=inputs)


def _edit_replayed_evaluation(
    *,
    cache: ResultCache,
    inputs: _EditReplayInputs,
) -> CacheEvaluation | None:
    if inputs.scopes.scoped or inputs.custom_rule_registrations or inputs.context.index is None:
        return None
    entries: dict[str, CacheIndexEntry] = inputs.entries
    sorted_targets: tuple[str, ...] = inputs.sorted_targets
    if len(entries) != len(sorted_targets) or any(path not in entries for path in sorted_targets):
        return None
    changed: frozenset[str] = frozenset(
        path
        for path in sorted_targets
        if inputs.source_fingerprints.get(path) is None
        or entries[path].source_fingerprint != inputs.source_fingerprints[path]
    )
    if not changed:
        return None
    surface: EditReplaySurface | None = cache.load_edit_surface(context=inputs.context)
    if surface is None:
        return None
    if not dependencies_are_current(
        observations=surface.observations,
        repo_root=inputs.tree.repo_root.path,
        states=inputs.states,
    ):
        return None
    fresh_evaluations: tuple[FileEvaluation, ...] = _fresh_edit_evaluations(
        inputs=inputs,
        changed=changed,
    )
    from strata.cache.results._helpers.conversion import (
        build_collection_contributions,
        restore_contribution_evaluation,
    )
    from strata.evaluation.main.collect_result import collect_file_evaluations

    fresh_collection: tuple[CachedCollectionContribution, ...] | None = (
        build_collection_contributions(
            evaluations=fresh_evaluations,
            repo_root=inputs.tree.repo_root.path,
        )
    )
    if fresh_collection is None:
        return None
    retained_contributions: tuple[CachedCollectionContribution, ...] = tuple(
        contribution
        for contribution in surface.contributions
        if contribution.path not in changed and contribution.path in entries
    )
    restored: tuple[FileEvaluation, ...] = tuple(
        restore_contribution_evaluation(
            contribution=contribution,
            source_fingerprint=entries[contribution.path].source_fingerprint,
            repo_root=inputs.tree.repo_root.path,
        )
        for contribution in retained_contributions
    )
    fresh_dependencies: list[ProjectDependency] = []
    for evaluation in fresh_evaluations:
        fresh_dependencies.extend(evaluation.dependencies)
    result: EvaluationResult = collect_file_evaluations(
        file_evaluations=(*restored, *fresh_evaluations),
        dependencies=tuple(fresh_dependencies),
        config=inputs.config,
        repo_root=inputs.tree.repo_root.path,
        evaluated_rule_codes=frozenset(rule.code for rule in inputs.evaluated_rules),
        selection=inputs.selection,
    )
    merged_collection: tuple[CachedCollectionContribution, ...] = tuple(
        sorted(
            (*retained_contributions, *fresh_collection),
            key=lambda contribution: contribution.path,
        )
    )
    publication: CacheStats = _publish_results(
        cache=cache,
        global_fingerprint=inputs.global_fingerprint,
        fresh_evaluations=fresh_evaluations,
        retained_entries=tuple(entries[path] for path in sorted_targets if path not in changed),
        retained_results=(),
        existing_index_fingerprint=inputs.context.index_fingerprint,
        retained_observations=surface.observations,
        collection=merged_collection,
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
            hits=len(sorted_targets) - len(changed),
            misses=0,
            invalidations=len(changed),
            writes=publication.writes,
            non_cacheable=publication.non_cacheable,
            storage_failed=publication.storage_failed,
            internal_error=publication.internal_error,
        ),
        surface_targets=sorted_targets if surface_ready else None,
        surface_index_fingerprint=publication.index_fingerprint if surface_ready else None,
    )


def _fresh_edit_evaluations(
    *,
    inputs: _EditReplayInputs,
    changed: frozenset[str],
) -> tuple[FileEvaluation, ...]:
    from strata.evaluation.main.build_project import build_evaluation_project
    from strata.evaluation.main.evaluate_target_chunk import evaluate_target_chunk

    changed_targets: tuple[EvaluationTarget, ...] = tuple(
        target
        for target in inputs.targets
        if relative_repository_path(
            path=target.scoped_file.path,
            repo_root=inputs.tree.repo_root.path,
        )
        in changed
    )
    project: EvaluationProjectAnalysis = build_evaluation_project(tree=inputs.tree)
    fresh_evaluations: list[FileEvaluation] = []
    for start in range(0, len(changed_targets), PREWARM_CHUNK_SIZE):
        chunk: tuple[EvaluationTarget, ...] = changed_targets[start : start + PREWARM_CHUNK_SIZE]
        fresh_evaluations.extend(
            evaluate_target_chunk(
                targets=chunk,
                ruleset=inputs.scopes.cacheable_ruleset,
                warning_rules=inputs.scopes.cacheable_warning_rules,
                config=inputs.config,
                tree=inputs.tree,
                project=project,
            )
        )
    return tuple(fresh_evaluations)


def _replayed_evaluation(
    *,
    cache: ResultCache,
    scopes: _RuleScopes,
    context: CheckCacheContext,
    entries: dict[str, CacheIndexEntry],
    sorted_targets: tuple[str, ...],
    source_fingerprints: dict[str, CacheFingerprint | None],
    repo_root: Path,
    states: DependencyStateCache,
    global_fingerprint: CacheFingerprint,
    target_count: int,
) -> CacheEvaluation | None:
    if scopes.scoped:
        return None
    if not _replay_manifest_is_current(
        context=context,
        entries=entries,
        sorted_targets=sorted_targets,
        source_fingerprints=source_fingerprints,
    ):
        return None
    replay_context: CheckCacheContext = cache.load_check_surface(
        global_fingerprint=global_fingerprint,
        context=context,
    )
    if not _replay_hit(
        context=replay_context,
        sorted_targets=sorted_targets,
        repo_root=repo_root,
        states=states,
    ):
        return None
    return CacheEvaluation(
        result=None,
        stats=CacheStats(hits=target_count),
        short_circuit=replay_context.output,
    )


def _materialized(
    *,
    item: FileEvaluation | CachedFileResult,
    repo_root: Path,
) -> FileEvaluation:
    from strata.cache.results._helpers.conversion import restore_file_evaluation
    from strata.evaluation.models import FileEvaluation

    if isinstance(item, FileEvaluation):
        return item
    return restore_file_evaluation(result=item, repo_root=repo_root)


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


def _target_decisions(
    *,
    targets: tuple[EvaluationTarget, ...],
    tree: DiscoveredTree,
    cache: ResultCache,
    entries: dict[str, CacheIndexEntry],
    source_fingerprints: dict[str, CacheFingerprint | None],
    loaded_results: dict[str, CachedFileResult | None],
    dependency_states: DependencyStateCache,
) -> tuple[_TargetDecision, ...]:
    decisions: list[_TargetDecision] = []
    for target in targets:
        path: str | None = relative_repository_path(
            path=target.scoped_file.path,
            repo_root=tree.repo_root.path,
        )
        source_fingerprint: CacheFingerprint | None = (
            source_fingerprints.get(path) if path is not None else None
        )
        entry: CacheIndexEntry | None = entries.get(path) if path is not None else None
        lookup: CacheLookup | None = None
        if entry is not None and source_fingerprint is not None:
            lookup = cache.loaded_candidate(
                entry=entry,
                source_fingerprint=source_fingerprint,
                result=loaded_results.get(entry.path),
                dependency_states=dependency_states,
            )
        decisions.append(_TargetDecision(target=target, entry=entry, lookup=lookup))
    return tuple(decisions)


def _rule_scopes(
    *,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
) -> _RuleScopes:
    fresh_ruleset: tuple[RuleSpec, ...] = _fresh_subset(ruleset)
    fresh_warning_rules: tuple[RuleSpec, ...] = _fresh_subset(warning_rules)
    return _RuleScopes(
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
    from strata.evaluation.main.evaluate_target import evaluate_target
    from strata.evaluation.main.merge_evaluations import merge_file_evaluations
    from strata.evaluation.models import EvaluationTarget

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


def _replay_hit(
    *,
    context: CheckCacheContext,
    sorted_targets: tuple[str, ...],
    repo_root: Path,
    states: DependencyStateCache,
) -> bool:
    if context.output is None or context.observations is None:
        return False
    if context.output.targets != sorted_targets:
        return False
    return dependencies_are_current(
        observations=context.observations,
        repo_root=repo_root,
        states=states,
    )


def _replay_manifest_is_current(
    *,
    context: CheckCacheContext,
    entries: dict[str, CacheIndexEntry],
    sorted_targets: tuple[str, ...],
    source_fingerprints: dict[str, CacheFingerprint | None],
) -> bool:
    if context.index is None or len(entries) != len(sorted_targets):
        return False
    for path in sorted_targets:
        entry: CacheIndexEntry | None = entries.get(path)
        fingerprint: CacheFingerprint | None = source_fingerprints.get(path)
        if entry is None or fingerprint is None or entry.source_fingerprint != fingerprint:
            return False
    return True


def _publish_results(
    *,
    cache: ResultCache,
    global_fingerprint: CacheFingerprint,
    fresh_evaluations: tuple[FileEvaluation, ...],
    retained_entries: tuple[CacheIndexEntry, ...],
    retained_results: tuple[CachedFileResult, ...],
    existing_index_fingerprint: CacheFingerprint | None,
    retained_observations: tuple[DependencyObservation, ...] | None = None,
    collection: tuple[CachedCollectionContribution, ...] | None = None,
) -> CacheStats:
    try:
        stats: CacheStats = cache.publish(
            global_fingerprint=global_fingerprint,
            evaluations=fresh_evaluations,
            retained_entries=retained_entries,
            retained_results=retained_results,
            retained_observations=retained_observations,
            collection=collection,
        )
        return (
            replace(stats, index_fingerprint=existing_index_fingerprint)
            if stats.index_fingerprint is None
            and not stats.storage_failed
            and not stats.internal_error
            else stats
        )
    except (CachePathError, CacheRecordError, TypeError, ValueError):
        return CacheStats(storage_failed=True, internal_error=True)


def _source_fingerprint(path: Path) -> CacheFingerprint | None:
    snapshot_hash: str | None = SNAPSHOT_TABLE.source_hash(path=path)
    if snapshot_hash is not None:
        return CacheFingerprint(value=snapshot_hash)
    try:
        return fingerprint_source(path.read_bytes())
    except OSError:
        return None
