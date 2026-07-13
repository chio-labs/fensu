"""Collect per-file evaluation outputs through global result contracts."""

from pathlib import Path

from strata.analysis.models import ProjectDependency
from strata.config.models import Config
from strata.evaluation._helpers.collection import collect_evaluation_result
from strata.evaluation.models import EvaluationResult, EvaluationSelection, FileEvaluation


def collect_file_evaluations(
    *,
    file_evaluations: tuple[FileEvaluation, ...],
    dependencies: tuple[ProjectDependency, ...],
    config: Config,
    repo_root: Path,
    selection: EvaluationSelection | None = None,
) -> EvaluationResult:
    """Return the complete sorted result for cached or fresh file outputs."""

    return collect_evaluation_result(
        file_evaluations=file_evaluations,
        dependencies=dependencies,
        config=config,
        repo_root=repo_root,
        selection=selection,
    )
