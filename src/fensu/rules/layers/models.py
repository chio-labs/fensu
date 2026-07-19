"""Layer boundary data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModuleOwnership:
    """Structural ownership inferred from one importable module path."""

    package: str | None
    owner_prefix: tuple[str, ...]
    domain: str | None
    first_role: str | None
    tail: tuple[str, ...]

    @property
    def owner(self) -> tuple[str, ...]:
        """Return the complete package-qualified owner."""

        if self.package is None:
            return self.owner_prefix
        return (self.package, *self.owner_prefix)
