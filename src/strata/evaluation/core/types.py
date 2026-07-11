"""Evaluation runtime protocols."""

from __future__ import annotations

from typing import Protocol

from strata.analysis.core.types import ProjectAnalysis
from strata.discovery.core.models import ScopedFile
from strata.evaluation.core.models import ParsedModule


class EvaluationProjectAnalysis(ProjectAnalysis, Protocol):
    """Project analysis with strict discovered-file parsing for evaluation."""

    def parsed_module(self, scoped_file: ScopedFile) -> ParsedModule:
        """Return one strict discovered-file parse."""
        ...
