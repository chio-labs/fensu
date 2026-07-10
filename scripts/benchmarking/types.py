"""Benchmarking type-layer declarations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from strata.discovery.core.models import ScopedFile
from strata.evaluation.core.models import ParsedModule
from strata.rules.authoring.models import Fault


class EvaluatorModule(Protocol):
    """Mutable evaluator functions instrumented by the benchmark profiler."""

    parse_scoped_file: Callable[[ScopedFile], ParsedModule]
    execute_rule: Callable[..., list[Fault]]
