"""Collect per-file evaluation outputs through global result contracts."""

from pathlib import Path

from strata.analysis.core.models import ProjectDependency
from strata.config.core.models import Config
from strata.evaluation.core.helpers.collection import collect_evaluation_result
from strata.evaluation.core.models import EvaluationResult, FileEvaluation


def collect_file_evaluations(
    *,
    file_evaluations: tuple[FileEvaluation, ...],
    dependencies: tuple[ProjectDependency, ...],
    config: Config,
    repo_root: Path,
) -> EvaluationResult:
    """Return the complete sorted result for cached or fresh file outputs."""

    return collect_evaluation_result(
        file_evaluations=file_evaluations,
        dependencies=dependencies,
        config=config,
        repo_root=repo_root,
    )
