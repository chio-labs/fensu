"""Structured models for CLI command orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from strata.analysis.models import ProjectDependency
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results.models import CachedCheckOutput, CacheStats
from strata.config.models import Config, LoadedConfig
from strata.discovery.models import DiscoveredTree
from strata.evaluation.models import EvaluationResult, FileEvaluation
from strata.rules.catalog.models import RuleSelection


@dataclass(frozen=True, slots=True)
class CheckInputs:
    """Configured catalogue and discovered tree for one check invocation."""

    loaded: LoadedConfig
    project_dir: Path
    rule_selection: RuleSelection
    config: Config
    tree: DiscoveredTree


@dataclass(frozen=True, slots=True)
class CheckEvaluation:
    """Evaluated diagnostics plus cache observability for one check run."""

    result: EvaluationResult | None
    stats: CacheStats | None
    disabled_reason: str | None
    short_circuit: CachedCheckOutput | None
    surface_targets: tuple[str, ...] | None
    global_fingerprint: CacheFingerprint | None
    surface_index_fingerprint: CacheFingerprint | None


@dataclass(frozen=True, slots=True)
class EvaluationWorkerRequest:
    """Everything one worker process needs to rebuild and evaluate a partition."""

    invocation_dir: str
    warn: bool
    paths: tuple[str, ...]
    cache_enabled: bool | None
    backend: str | None
    native_threads: int
    partition: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvaluationWorkerParseFailure:
    """One picklable parse failure carried back from a worker process."""

    path: str
    message: str
    line: int | None
    column: int | None


@dataclass(frozen=True, slots=True)
class EvaluationWorkerOutcome:
    """Raw partition output shipped from one worker process."""

    file_evaluations: tuple[FileEvaluation, ...]
    dependencies: tuple[ProjectDependency, ...]
    parse_failure: EvaluationWorkerParseFailure | None
