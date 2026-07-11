"""Coordinate cached and fresh per-file evaluation results."""

from __future__ import annotations

from pathlib import Path

from strata.analysis.core.models import ProjectDependency
from strata.cache.fingerprints.main.source import fingerprint_source
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results.classes.result_cache import ResultCache
from strata.cache.results.helpers.conversion import restore_file_evaluation
from strata.cache.results.helpers.paths import relative_repository_path
from strata.cache.results.models import (
    CachedFileResult,
    CacheEvaluation,
    CacheIndex,
    CacheIndexEntry,
    CacheLookup,
    CacheStats,
)
from strata.cache.results.types import DependencyStateCache
from strata.config.core.models import Config
from strata.discovery.core.models import DiscoveredTree
from strata.evaluation.core.main.build_project import build_evaluation_project
from strata.evaluation.core.main.collect_result import collect_file_evaluations
from strata.evaluation.core.main.evaluate import evaluate
from strata.evaluation.core.main.evaluate_file import evaluate_discovered_file
from strata.evaluation.core.models import EvaluationResult, FileEvaluation
from strata.evaluation.core.types import EvaluationProjectAnalysis
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import RuleKind


def run_cached_evaluation(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    config: Config,
    global_fingerprint: CacheFingerprint,
) -> CacheEvaluation:
    """Return a complete evaluation using only fully validated file-result hits."""

    if any(rule.kind is RuleKind.CUSTOM for rule in ruleset):
        result: EvaluationResult = evaluate(tree=tree, ruleset=ruleset, config=config)
        return CacheEvaluation(
            result=result,
            stats=CacheStats(non_cacheable=len(tree.files)),
        )
    cache: ResultCache = ResultCache(repo_root=tree.repo_root.path)
    index: CacheIndex | None = cache.load_index(global_fingerprint=global_fingerprint)
    entries: dict[str, CacheIndexEntry] = (
        {entry.path: entry for entry in index.entries} if index is not None else {}
    )
    discovered_paths: set[str] = set()
    for scoped_file in tree.files:
        discovered_path: str | None = relative_repository_path(
            path=scoped_file.path,
            repo_root=tree.repo_root.path,
        )
        if discovered_path is not None:
            discovered_paths.add(discovered_path)
    loaded_entries: tuple[CacheIndexEntry, ...] = tuple(
        entry for path, entry in entries.items() if path in discovered_paths
    )
    loaded_results: dict[str, CachedFileResult | None] = cache.load_results(
        global_fingerprint=global_fingerprint,
        entries=loaded_entries,
    )
    project: EvaluationProjectAnalysis = build_evaluation_project(tree=tree)
    file_evaluations: list[FileEvaluation] = []
    fresh_evaluations: list[FileEvaluation] = []
    retained_entries: list[CacheIndexEntry] = []
    dependency_states: DependencyStateCache = {}
    hits: int = 0
    misses: int = 0
    invalidations: int = sum(path not in discovered_paths for path in entries)
    for scoped_file in tree.files:
        path: str | None = relative_repository_path(
            path=scoped_file.path,
            repo_root=tree.repo_root.path,
        )
        source_fingerprint: CacheFingerprint | None = _source_fingerprint(scoped_file.path)
        entry: CacheIndexEntry | None = entries.get(path) if path is not None else None
        lookup: CacheLookup | None = None
        if entry is not None and source_fingerprint is not None:
            lookup = cache.loaded_candidate(
                entry=entry,
                source_fingerprint=source_fingerprint,
                result=loaded_results.get(entry.path),
                dependency_states=dependency_states,
            )
        if lookup is not None and lookup.result is not None:
            file_evaluations.append(
                restore_file_evaluation(result=lookup.result, repo_root=tree.repo_root.path)
            )
            hits += 1
            if entry is not None:
                retained_entries.append(entry)
            continue
        if lookup is None or lookup.missed:
            misses += 1
        else:
            invalidations += 1
        fresh: FileEvaluation = evaluate_discovered_file(
            scoped_file=scoped_file,
            ruleset=ruleset,
            config=config,
            tree=tree,
            project=project,
        )
        file_evaluations.append(fresh)
        fresh_evaluations.append(fresh)
    evaluations: tuple[FileEvaluation, ...] = tuple(file_evaluations)
    collected_dependencies: list[ProjectDependency] = []
    for file_evaluation in evaluations:
        collected_dependencies.extend(file_evaluation.dependencies)
    dependencies: tuple[ProjectDependency, ...] = tuple(collected_dependencies)
    result = collect_file_evaluations(
        file_evaluations=evaluations,
        dependencies=dependencies,
        config=config,
        repo_root=tree.repo_root.path,
    )
    publication: CacheStats = cache.publish(
        global_fingerprint=global_fingerprint,
        evaluations=tuple(fresh_evaluations),
        retained_entries=tuple(retained_entries),
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
        ),
    )


def _source_fingerprint(path: Path) -> CacheFingerprint | None:
    try:
        return fingerprint_source(path.read_bytes())
    except OSError:
        return None
