"""Merge per-file evaluation outputs owned by one source path."""

from __future__ import annotations

from fensu.analysis.models import ProjectDependency
from fensu.evaluation.models import (
    FileEvaluation,
    RuleExceptionKey,
    ThresholdOverrideUse,
)
from fensu.rules.authoring.models import Fault


def merge_file_evaluations(*, evaluations: tuple[FileEvaluation, ...]) -> FileEvaluation:
    """Combine same-file evaluation outputs into one deduplicated record."""

    first: FileEvaluation = evaluations[0]
    faults: list[Fault] = []
    warnings: list[Fault] = []
    applied_exception_keys: set[RuleExceptionKey] = set()
    dependencies: dict[ProjectDependency, None] = {}
    threshold_override_uses: dict[ThresholdOverrideUse, None] = {}
    for evaluation in evaluations:
        faults.extend(evaluation.faults)
        warnings.extend(evaluation.warnings)
        applied_exception_keys.update(evaluation.applied_exception_keys)
        dependencies.update(dict.fromkeys(evaluation.dependencies))
        threshold_override_uses.update(dict.fromkeys(evaluation.threshold_override_uses))
    return FileEvaluation(
        path=first.path,
        source_fingerprint=first.source_fingerprint,
        faults=tuple(faults),
        warnings=tuple(warnings),
        applied_exception_keys=tuple(
            sorted(
                applied_exception_keys,
                key=lambda key: (key.rule, key.path, key.symbol or ""),
            )
        ),
        dependencies=tuple(dependencies),
        threshold_override_uses=tuple(threshold_override_uses),
    )
