"""Process-wide operation counting with zero cost while disabled."""

from __future__ import annotations


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

    def record(self, *, operation: str) -> None:
        """Count one operation while counting is enabled."""

        if self._enabled:
            self._counts[operation] = self._counts.get(operation, 0) + 1

    def snapshot(self) -> dict[str, int]:
        """Return a copy of the recorded operation counts."""

        return dict(self._counts)
