"""Measure named engine operations performed by one action."""

from __future__ import annotations

from collections.abc import Callable

from strata.instrumentation.constants import OPERATION_COUNTERS


def measure_operations(*, operation: Callable[[], object]) -> dict[str, int]:
    """Run one action while counting instrumented engine operations."""

    OPERATION_COUNTERS.enable()
    try:
        _ = operation()
        return OPERATION_COUNTERS.snapshot()
    finally:
        OPERATION_COUNTERS.disable()
