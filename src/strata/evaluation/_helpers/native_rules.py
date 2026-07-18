"""Prepare Python-owned context for native per-file rule evaluation."""

from __future__ import annotations

from pathlib import Path

from strata.config.main.resolve_threshold import resolve_threshold
from strata.config.models import Config, ThresholdResolution
from strata.discovery.main.position import position_facts
from strata.discovery.models import PositionFacts
from strata.evaluation.models import EvaluationTarget, ThresholdOverrideUse
from strata.evaluation.types import NativeCoreRuleRequest, NativeThresholdValues
from strata.rules.authoring.types import Threshold

_threshold_by_code: dict[str, Threshold] = {
    "SFS001": Threshold.MAX_STATEMENTS,
    "SFS002": Threshold.MAX_DISTINCT_CALLS,
    "SFS003": Threshold.MAX_LOCALS,
    "SFS010": Threshold.MAX_ARGUMENTS,
    "SFS011": Threshold.MAX_STATEMENTS_GLOBAL,
    "SFS120": Threshold.MAX_POSITIONAL_ARGS,
}
_main_only_threshold_codes: frozenset[str] = frozenset({"SFS001", "SFS002", "SFS003"})
_maximum_native_metric: int = 2**32 - 1
_native_naming_codes: frozenset[str] = frozenset({"SFN001", "SFN002", "SFN003", "SFN004"})


def prepare_native_rule_request(
    *,
    target: EvaluationTarget,
    program: object | None,
    codes: tuple[str, ...],
    config: Config,
    repo_root: Path,
) -> tuple[NativeCoreRuleRequest | None, tuple[ThresholdOverrideUse, ...]]:
    """Build one raw native request and retain threshold override provenance."""

    if program is None:
        return None, ()
    position: PositionFacts = position_facts(target.scoped_file)
    repository_path: str = target.scoped_file.path.relative_to(repo_root).as_posix()
    thresholds: NativeThresholdValues = {}
    uses: list[ThresholdOverrideUse] = []
    for code in codes:
        threshold: Threshold | None = _threshold_by_code.get(code)
        if threshold is None or (
            code in _main_only_threshold_codes and not position.is_main_module
        ):
            continue
        resolution: ThresholdResolution = resolve_threshold(
            config=config,
            name=threshold,
            path=repository_path,
            role=position.role,
        )
        thresholds[threshold.value] = min(resolution.effective_value, _maximum_native_metric)
        if (
            resolution.matched_pattern is not None
            and resolution.reason is not None
            and resolution.override_order is not None
        ):
            uses.append(
                ThresholdOverrideUse(
                    threshold=resolution.threshold,
                    effective_value=resolution.effective_value,
                    matched_pattern=resolution.matched_pattern,
                    reason=resolution.reason,
                    override_order=resolution.override_order,
                    repository_path=resolution.repository_path,
                )
            )
    request: NativeCoreRuleRequest = (
        program,
        list(codes),
        target.scoped_file.scope.value,
        position.role,
        position.is_main_module,
        thresholds,
        repository_path,
        list(config.contracts.items()) if _native_naming_codes.intersection(codes) else [],
    )
    return request, tuple(uses)
