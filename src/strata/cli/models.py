"""Structured models for CLI command orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results.models import CachedCheckOutput, CacheStats
from strata.config.models import Config, LoadedConfig
from strata.discovery.models import DiscoveredTree
from strata.evaluation.models import EvaluationResult
from strata.rules.catalog.models import RuleSelection


@dataclass(frozen=True, slots=True)
class CheckInputs:
    """Configured catalogue and discovered tree for one check invocation."""

    loaded: LoadedConfig
    project_dir: Path
    rule_selection: RuleSelection
    config: Config
    tree: DiscoveredTree
    memory_result: object | None


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
