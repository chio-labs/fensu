"""Evaluate a ruleset over a discovered tree."""

from __future__ import annotations

from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.evaluation._helpers.collection import collect_evaluation_result
from strata.evaluation._helpers.file_evaluation import evaluate_file
from strata.evaluation._helpers.project_analysis import build_project_analysis
from strata.evaluation.main.select_files import select_evaluation_files
from strata.evaluation.models import EvaluationResult, EvaluationSelection, FileEvaluation
from strata.evaluation.types import EvaluationProjectAnalysis
from strata.rules.authoring.models import RuleSpec


def evaluate(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    config: Config,
) -> EvaluationResult:
    """Evaluate selected rules over discovered Python files."""

    file_evaluations: list[FileEvaluation] = []
    selection: EvaluationSelection = select_evaluation_files(tree=tree, config=config.evaluation)
    project: EvaluationProjectAnalysis = build_project_analysis(tree=tree)
    for scoped_file in selection.files:
        file_result: FileEvaluation = evaluate_file(
            scoped_file=scoped_file,
            ruleset=ruleset,
            config=config,
            tree=tree,
            project=project,
        )
        file_evaluations.append(file_result)
    return collect_evaluation_result(
        file_evaluations=tuple(file_evaluations),
        dependencies=project.dependencies(),
        config=config,
        repo_root=tree.repo_root.path,
        selection=selection,
    )
