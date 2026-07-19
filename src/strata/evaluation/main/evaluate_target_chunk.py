"""Evaluate one prewarmed target chunk through native and Python rule ownership."""

from __future__ import annotations

from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.evaluation.main._evaluate_native_core_rules import evaluate_native_core_rules
from strata.evaluation.main.evaluate_target import evaluate_target
from strata.evaluation.models import EvaluationTarget, FileEvaluation, NativeCoreRuleEvaluation
from strata.evaluation.types import EvaluationProjectAnalysis
from strata.rules.authoring.models import RuleSpec


def evaluate_target_chunk(
    *,
    targets: tuple[EvaluationTarget, ...],
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
    config: Config,
    tree: DiscoveredTree,
    project: EvaluationProjectAnalysis,
) -> tuple[FileEvaluation, ...]:
    """Evaluate one bounded target chunk through its registered execution owners."""

    scope_roots: tuple[tuple[str, str], ...] = (
        *(
            ("root", source.path.relative_to(tree.repo_root.path).as_posix())
            for source in tree.layout.runtime_sources
        ),
        *(
            ("tooling", source.path.relative_to(tree.repo_root.path).as_posix())
            for source in tree.layout.tooling_sources
        ),
        *(
            ("test", root.path.relative_to(tree.repo_root.path).as_posix())
            for root in tree.layout.test_roots
        ),
    )
    native_evaluations: tuple[NativeCoreRuleEvaluation, ...] = evaluate_native_core_rules(
        targets=targets,
        ruleset=ruleset,
        warning_rules=warning_rules,
        config=config,
        repo_root=tree.repo_root.path,
        tooling_packages=tuple(source.package_name for source in tree.layout.tooling_sources),
        project=project,
        scope_roots=scope_roots,
    )
    return tuple(
        evaluate_target(
            target=target,
            ruleset=ruleset,
            warning_rules=warning_rules,
            config=config,
            tree=tree,
            project=project,
            native_evaluation=native_evaluation,
        )
        for target, native_evaluation in zip(targets, native_evaluations, strict=True)
    )
