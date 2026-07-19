"""Process-wide operation counting with zero cost while disabled."""

from __future__ import annotations

import time
from collections.abc import Callable


class OperationCounters:
    """Count named engine operations while explicitly enabled."""

    def __init__(self) -> None:
        """Start disabled with no recorded operations."""

        self._enabled: bool = False
        self._counts: dict[str, int] = {}

    def enable(self) -> None:
        """Reset recorded operations and start counting."""

        self._counts = {}
        self._enabled = True

    def disable(self) -> None:
        """Stop counting without clearing recorded operations."""

        self._enabled = False

    def record(self, *, operation: str, amount: int = 1) -> None:
        """Count operations while counting is enabled."""

        if self._enabled and amount:
            self._counts[operation] = self._counts.get(operation, 0) + amount

    def measure[T](self, *, operation: str, callback: Callable[[], T]) -> T:
        """Measure one phase only while operation counting is enabled."""

        if not self._enabled:
            return callback()
        started: int = time.perf_counter_ns()
        try:
            return callback()
        finally:
            self.record(operation=operation, amount=time.perf_counter_ns() - started)

    def snapshot(self) -> dict[str, int]:
        """Return a copy of the recorded operation counts."""

        return dict(self._counts)
