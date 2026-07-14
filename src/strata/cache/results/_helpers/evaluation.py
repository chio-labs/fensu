"""Coordinate cached and fresh per-file evaluation results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from strata.analysis.models import ProjectDependency
from strata.cache.fingerprints.main.source import fingerprint_source
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results._helpers.conversion import restore_file_evaluation
from strata.cache.results._helpers.dependencies import dependencies_are_current
from strata.cache.results._helpers.paths import relative_repository_path
from strata.cache.results.classes.result_cache import ResultCache
from strata.cache.results.models import (
    CachedFileResult,
    CacheEvaluation,
    CacheIndex,
    CacheIndexEntry,
    CacheLookup,
    CacheStats,
    CheckCacheContext,
)
from strata.cache.results.types import DependencyStateCache
from strata.cache.storage.exceptions import CachePathError, CacheRecordError
from strata.config.models import Config
from strata.discovery.models import DiscoveredTree, ScopedFile
from strata.evaluation.constants import PREWARM_CHUNK_SIZE
from strata.evaluation.main.build_project import build_evaluation_project
from strata.evaluation.main.build_targets import build_evaluation_targets
from strata.evaluation.main.collect_result import collect_file_evaluations
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.main.evaluate_target import evaluate_target
from strata.evaluation.main.merge_evaluations import merge_file_evaluations
from strata.evaluation.main.prewarm_files import prewarm_evaluation_files
from strata.evaluation.main.select_files import select_evaluation_files
from strata.evaluation.models import (
    EvaluationResult,
    EvaluationSelection,
    EvaluationTarget,
    FileEvaluation,
)
from strata.evaluation.types import EvaluationProjectAnalysis
from strata.rules.authoring.models import CustomRuleRegistration, RuleSpec
from strata.rules.authoring.types import RuleKind


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
    context: CheckCacheContext = cache.load_check_context(global_fingerprint=global_fingerprint)
    index: CacheIndex | None = context.index
    entries: dict[str, CacheIndexEntry] = (
        {entry.path: entry for entry in index.entries} if index is not None else {}
    )
    target_paths: set[str] = set()
    source_fingerprints: dict[str, CacheFingerprint | None] = {}
    for target in targets:
        discovered_path: str | None = relative_repository_path(
            path=target.scoped_file.path,
            repo_root=tree.repo_root.path,
        )
        if discovered_path is not None:
            target_paths.add(discovered_path)
            source_fingerprints[discovered_path] = _source_fingerprint(target.scoped_file.path)
    sorted_targets: tuple[str, ...] = tuple(sorted(target_paths))
    dependency_states: DependencyStateCache = {}
    if not scopes.scoped and _replay_hit(
        context=context,
        entries=entries,
        sorted_targets=sorted_targets,
        source_fingerprints=source_fingerprints,
        repo_root=tree.repo_root.path,
        states=dependency_states,
    ):
        return CacheEvaluation(
            result=None,
            stats=CacheStats(hits=len(targets)),
            short_circuit=context.output,
        )
    loaded_entries: tuple[CacheIndexEntry, ...] = tuple(
        entry for path, entry in entries.items() if path in target_paths
    )
    loaded_results: dict[str, CachedFileResult | None] = cache.load_results(
        global_fingerprint=global_fingerprint,
        entries=loaded_entries,
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
        dependency_states=dependency_states,
    )
    miss_files: tuple[ScopedFile, ...] = tuple(
        decision.target.scoped_file
        for decision in decisions
        if decision.lookup is None or decision.lookup.result is None
    )
    evaluated_misses: int = 0
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
        if evaluated_misses % PREWARM_CHUNK_SIZE == 0:
            prewarm_evaluation_files(
                project=project,
                scoped_files=miss_files[evaluated_misses : evaluated_misses + PREWARM_CHUNK_SIZE],
            )
        evaluated_misses += 1
        fresh: FileEvaluation = evaluate_target(
            target=decision.target,
            ruleset=scopes.cacheable_ruleset,
            warning_rules=scopes.cacheable_warning_rules,
            config=config,
            tree=tree,
            project=project,
        )
        ordered_results.append(fresh)
        fresh_evaluations.append(fresh)
    if (
        not scopes.scoped
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
    publication: CacheStats = _publish_results(
        cache=cache,
        global_fingerprint=global_fingerprint,
        fresh_evaluations=tuple(fresh_evaluations),
        retained_entries=tuple(retained_entries),
        retained_results=tuple(retained_results),
    )
    surface_ready: bool = (
        not scopes.scoped
        and publication.non_cacheable == 0
        and not publication.storage_failed
        and not publication.internal_error
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
    )


def _materialized(
    *,
    item: FileEvaluation | CachedFileResult,
    repo_root: Path,
) -> FileEvaluation:
    if isinstance(item, FileEvaluation):
        return item
    return restore_file_evaluation(result=item, repo_root=repo_root)


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
    if not target.direct:
        return evaluation
    fresh: FileEvaluation = evaluate_target(
        target=EvaluationTarget(scoped_file=target.scoped_file, direct=True),
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
    entries: dict[str, CacheIndexEntry],
    sorted_targets: tuple[str, ...],
    source_fingerprints: dict[str, CacheFingerprint | None],
    repo_root: Path,
    states: DependencyStateCache,
) -> bool:
    if context.output is None or context.observations is None:
        return False
    if context.output.targets != sorted_targets or len(entries) != len(sorted_targets):
        return False
    for path in sorted_targets:
        entry: CacheIndexEntry | None = entries.get(path)
        fingerprint: CacheFingerprint | None = source_fingerprints.get(path)
        if entry is None or fingerprint is None or entry.source_fingerprint != fingerprint:
            return False
    return dependencies_are_current(
        observations=context.observations,
        repo_root=repo_root,
        states=states,
    )


def _publish_results(
    *,
    cache: ResultCache,
    global_fingerprint: CacheFingerprint,
    fresh_evaluations: tuple[FileEvaluation, ...],
    retained_entries: tuple[CacheIndexEntry, ...],
    retained_results: tuple[CachedFileResult, ...],
) -> CacheStats:
    try:
        return cache.publish(
            global_fingerprint=global_fingerprint,
            evaluations=fresh_evaluations,
            retained_entries=retained_entries,
            retained_results=retained_results,
        )
    except (CachePathError, CacheRecordError, TypeError, ValueError):
        return CacheStats(storage_failed=True, internal_error=True)


def _source_fingerprint(path: Path) -> CacheFingerprint | None:
    try:
        return fingerprint_source(path.read_bytes())
    except OSError:
        return None
