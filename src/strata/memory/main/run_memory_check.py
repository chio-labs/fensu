"""Validate and render canonical Strata Memory sources."""

from __future__ import annotations

from strata.memory.main.check_memory import check_memory
from strata.memory.main.render_memory_check import render_memory_check
from strata.memory.models import MemoryCheckResult
from strata.reporting.models import RenderedReport


def run_memory_check(*, use_color: bool = False) -> RenderedReport:
    """Return the rendered direct-source memory validation report."""

    checked: MemoryCheckResult = check_memory()
    return render_memory_check(result=checked, use_color=use_color)
