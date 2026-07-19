"""Validate and render canonical Fensu Memory sources."""

from __future__ import annotations

from fensu.memory.main.check_memory import check_memory
from fensu.memory.main.render_memory_check import render_memory_check
from fensu.memory.models import MemoryCheckResult
from fensu.reporting.models import RenderedReport


def run_memory_check(*, use_color: bool = False) -> RenderedReport:
    """Return the rendered direct-source memory validation report."""

    checked: MemoryCheckResult = check_memory()
    return render_memory_check(result=checked, use_color=use_color)
