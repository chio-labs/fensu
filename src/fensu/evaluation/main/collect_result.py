"""Collect per-file evaluation outputs through global result contracts."""

from pathlib import Path

from fensu.analysis.models import ProjectDependency
from fensu.config.models import Config
from fensu.evaluation._helpers.collection import collect_evaluation_result
from fensu.evaluation.models import (
    EvaluationResult,
    EvaluationSelection,
    FileEvaluation,
    ProjectEvaluation,
)


def collect_file_evaluations(
    *,
    file_evaluations: tuple[FileEvaluation, ...],
    dependencies: tuple[ProjectDependency, ...],
    config: Config,
    repo_root: Path,
    project_root: Path | None = None,
    evaluated_rule_codes: frozenset[str] | None = None,
    project_rule_codes: frozenset[str] = frozenset(),
    selection: EvaluationSelection | None = None,
    project_evaluation: ProjectEvaluation | None = None,
) -> EvaluationResult:
    """Return the complete sorted result for cached or fresh file outputs."""

    return collect_evaluation_result(
        file_evaluations=file_evaluations,
        dependencies=dependencies,
        config=config,
        repo_root=repo_root,
        project_root=project_root,
        evaluated_rule_codes=evaluated_rule_codes,
        project_rule_codes=project_rule_codes,
        selection=selection,
        project_evaluation=project_evaluation,
    )
