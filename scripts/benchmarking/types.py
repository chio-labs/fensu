"""Benchmarking type-layer declarations."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Protocol

from fensu.evaluation.models import ExternalAnalysisBuild, ParsedModule
from fensu.rules.authoring.models import Fault


class OperationProfileMode(StrEnum):
    """Supported cache states for deterministic operation profiling."""

    UNCACHED = "uncached"
    COLD = "cold"
    WARM = "warm"


class EvaluatorModule(Protocol):
    """Mutable evaluator functions instrumented by the benchmark profiler."""

    execute_rule: Callable[..., list[Fault]]


class ProjectAnalysisModule(Protocol):
    """Mutable project parser function instrumented by the benchmark profiler."""

    parse_scoped_file: Callable[..., ParsedModule]
    build_external_analysis: Callable[..., ExternalAnalysisBuild]
