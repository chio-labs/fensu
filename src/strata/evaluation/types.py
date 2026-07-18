"""Evaluation runtime protocols."""

from __future__ import annotations

from typing import Protocol

from strata.analysis.types import ProjectAnalysis
from strata.discovery.models import ScopedFile
from strata.evaluation.models import ParsedModule
from strata.rules.authoring.models import Fault

type NativeFaultRow = tuple[str, int, int, str | None]
type NativeFaultsByCode = dict[str, tuple[Fault, ...]]


class EvaluationProjectAnalysis(ProjectAnalysis, Protocol):
    """Project analysis with strict discovered-file parsing for evaluation."""

    def parsed_module(self, scoped_file: ScopedFile) -> ParsedModule:
        """Return one strict discovered-file parse."""
        ...

    def prewarm(self, *, parsed: ParsedModule) -> None:
        """Adopt one pre-parsed discovered module for later single-use retrieval."""
        ...
