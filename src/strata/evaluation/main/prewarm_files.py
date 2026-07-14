"""Batch-prewarm native parses for upcoming evaluation files."""

from __future__ import annotations

from strata.discovery.models import ScopedFile
from strata.evaluation._helpers.parsing import prewarm_scoped_files
from strata.evaluation.types import EvaluationProjectAnalysis


def prewarm_evaluation_files(
    *,
    project: EvaluationProjectAnalysis,
    scoped_files: tuple[ScopedFile, ...],
) -> None:
    """Seed the shared project analysis with natively pre-parsed files."""

    prewarm_scoped_files(project=project, scoped_files=scoped_files)
