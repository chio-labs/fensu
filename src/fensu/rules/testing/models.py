"""Public structured models for custom-rule pipeline tests."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from fensu.analysis.models import ProjectDependency
from fensu.rules.authoring.models import Fault


@dataclass(frozen=True, slots=True)
class RuleFile:
    """One supporting Python file available to project queries."""

    path: str
    source: str


@dataclass(frozen=True, slots=True)
class RuleCase:
    """One primary source and its expected custom-rule fault count."""

    description: str
    source: str
    expected_fault_count: int
    path: str = "src/example/main/example.py"
    scope: str = "root"
    scope_root: str | None = None
    files: tuple[RuleFile, ...] = ()
    config: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class RuleResult:
    """Stable custom-rule findings and observed project dependencies."""

    faults: tuple[Fault, ...]
    dependencies: tuple[ProjectDependency, ...]

    @property
    def fault_count(self) -> int:
        """Return the number of faults emitted for the primary source."""

        return len(self.faults)
