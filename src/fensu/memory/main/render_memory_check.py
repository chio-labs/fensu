"""Render Fensu Memory findings through the standard diagnostic language."""

from __future__ import annotations

from pathlib import Path

from fensu.memory.models import MemoryCheckResult, MemoryDiagnostic
from fensu.reporting.main.render import render
from fensu.reporting.models import RenderedReport
from fensu.rules.authoring.models import Fault


def render_memory_check(*, result: MemoryCheckResult, use_color: bool = False) -> RenderedReport:
    """Render stable memory findings and their blocking count."""

    faults: tuple[Fault, ...] = tuple(
        _to_fault(
            diagnostic=diagnostic,
            repository_root=result.project.repository_root,
        )
        for diagnostic in result.diagnostics
    )
    return render(
        faults=faults,
        root=result.project.repository_root,
        use_color=use_color,
    )


def _to_fault(*, diagnostic: MemoryDiagnostic, repository_root: Path) -> Fault:
    return Fault(
        code=diagnostic.code,
        path=repository_root / diagnostic.repository_relative_path,
        message=diagnostic.message,
        line=diagnostic.line,
        column=diagnostic.column,
        remediation=diagnostic.remediation,
    )
