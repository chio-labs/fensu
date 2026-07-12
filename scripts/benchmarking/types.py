"""Benchmarking type-layer declarations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from strata.evaluation.models import ExternalAnalysisBuild, ParsedModule
from strata.rules.authoring.models import Fault


class EvaluatorModule(Protocol):
    """Mutable evaluator functions instrumented by the benchmark profiler."""

    execute_rule: Callable[..., list[Fault]]


class ProjectAnalysisModule(Protocol):
    """Mutable project parser function instrumented by the benchmark profiler."""

    parse_scoped_file: Callable[..., ParsedModule]
    build_external_analysis: Callable[..., ExternalAnalysisBuild]
