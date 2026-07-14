"""Validate budget ceilings and cross-scenario invariants."""

from __future__ import annotations

from scripts.perfbudget.constants import (
    COLD_SCENARIO,
    DENSE_COLD_SCENARIO,
    DENSE_WARM_SCENARIO,
    EDIT_SCENARIO,
    FAULT_EXIT_CODE,
    UNCACHED_SCENARIO,
    WARM_MISS_FREE_FRAGMENT,
    WARM_SCENARIO,
    WARM_WRITE_FREE_FRAGMENT,
)
from scripts.perfbudget.models import BudgetSpec, ScenarioFailure, ScenarioResult


def budget_failures(
    *,
    spec: BudgetSpec,
    results: dict[str, ScenarioResult],
) -> tuple[ScenarioFailure, ...]:
    """Return every violated ceiling or invariant across measured scenarios."""

    ceilings: dict[str, float] = {
        UNCACHED_SCENARIO: spec.uncached_ceiling,
        COLD_SCENARIO: spec.cold_ceiling,
        WARM_SCENARIO: spec.warm_ceiling,
        EDIT_SCENARIO: spec.edit_ceiling,
        DENSE_COLD_SCENARIO: spec.cold_ceiling,
        DENSE_WARM_SCENARIO: spec.warm_ceiling,
    }
    failures: list[ScenarioFailure] = []
    for name, ceiling in ceilings.items():
        result: ScenarioResult = results[name]
        if result.exit_code != FAULT_EXIT_CODE:
            failures.append(
                ScenarioFailure(
                    scenario=name,
                    reason=f"exit code {result.exit_code} != {FAULT_EXIT_CODE}",
                )
            )
        if result.seconds > ceiling:
            failures.append(
                ScenarioFailure(
                    scenario=name,
                    reason=f"{result.seconds:.2f}s exceeded the {ceiling:.2f}s ceiling",
                )
            )
    failures.extend(_identity_failures(results=results))
    failures.extend(_warm_purity_failures(results=results))
    return tuple(failures)


def _identity_failures(*, results: dict[str, ScenarioResult]) -> tuple[ScenarioFailure, ...]:
    reference: ScenarioResult = results[UNCACHED_SCENARIO]
    failures: list[ScenarioFailure] = []
    for name in (COLD_SCENARIO, WARM_SCENARIO):
        if results[name].output_sha256 != reference.output_sha256:
            failures.append(
                ScenarioFailure(
                    scenario=name,
                    reason="rendered output diverged from the uncached run",
                )
            )
    dense_cold: ScenarioResult = results[DENSE_COLD_SCENARIO]
    if results[DENSE_WARM_SCENARIO].output_sha256 != dense_cold.output_sha256:
        failures.append(
            ScenarioFailure(
                scenario=DENSE_WARM_SCENARIO,
                reason="rendered output diverged from the dense cold run",
            )
        )
    return tuple(failures)


def _warm_purity_failures(*, results: dict[str, ScenarioResult]) -> tuple[ScenarioFailure, ...]:
    warm: ScenarioResult = results[WARM_SCENARIO]
    failures: list[ScenarioFailure] = []
    if WARM_MISS_FREE_FRAGMENT not in warm.cache_stats:
        failures.append(
            ScenarioFailure(scenario=WARM_SCENARIO, reason=f"stats missed: {warm.cache_stats}")
        )
    if WARM_WRITE_FREE_FRAGMENT not in warm.cache_stats:
        failures.append(
            ScenarioFailure(scenario=WARM_SCENARIO, reason=f"stats wrote: {warm.cache_stats}")
        )
    return tuple(failures)
