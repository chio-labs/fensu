"""Assemble and persist complete rendered check stdout surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from fensu.cache.fingerprints.models import CacheFingerprint
from fensu.cache.results.classes.result_cache import ResultCache
from fensu.cli._helpers.check_reporting import render_check_result
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation.models import EvaluationResult
from fensu.reporting.models import RenderedReport


@dataclass(frozen=True, slots=True)
class _CheckStdout:
    """One complete check stdout payload and its blocking fault count."""

    text: str
    fault_count: int


def check_stdout_text(
    *,
    result: EvaluationResult,
    tree: DiscoveredTree,
    use_color: bool,
    show_warnings: bool,
) -> tuple[str, int]:
    """Return the complete check stdout payload and its blocking fault count."""

    rendered: _CheckStdout = _rendered_stdout(
        result=result,
        tree=tree,
        use_color=use_color,
        show_warnings=show_warnings,
    )
    return rendered.text, rendered.fault_count


def persist_check_output(
    *,
    repo_root: Path,
    global_fingerprint: CacheFingerprint,
    targets: tuple[str, ...],
    result: EvaluationResult,
    tree: DiscoveredTree,
    show_warnings: bool,
    selected_output: str,
    selected_fault_count: int,
    selected_use_color: bool,
    expected_index_fingerprint: CacheFingerprint,
) -> bool:
    """Store both rendered stdout variants for the current cache generation."""

    selected: _CheckStdout = _CheckStdout(
        text=selected_output,
        fault_count=selected_fault_count,
    )
    if selected_use_color:
        color: _CheckStdout = selected
        plain: _CheckStdout = _rendered_stdout(
            result=result,
            tree=tree,
            use_color=False,
            show_warnings=show_warnings,
        )
    else:
        plain = selected
        color = _rendered_stdout(
            result=result,
            tree=tree,
            use_color=True,
            show_warnings=show_warnings,
        )
    return ResultCache(repo_root=repo_root).store_check_output(
        global_fingerprint=global_fingerprint,
        targets=targets,
        plain_output=plain.text,
        color_output=color.text,
        exit_code=1 if plain.fault_count else 0,
        expected_index_fingerprint=expected_index_fingerprint,
    )


def write_memory_check_result(*, stdout: TextIO, result: object | None, use_color: bool) -> int:
    """Append enabled memory findings without adding them to architecture caches."""

    if result is None:
        return 0
    from fensu.memory.main.render_memory_check import render_memory_check
    from fensu.memory.models import MemoryCheckResult

    if not isinstance(result, MemoryCheckResult) or not result.diagnostics:
        return 0

    report: RenderedReport = render_memory_check(result=result, use_color=use_color)
    stdout.write(f"\n{report.text}\n")
    return report.fault_count


def _rendered_stdout(
    *,
    result: EvaluationResult,
    tree: DiscoveredTree,
    use_color: bool,
    show_warnings: bool,
) -> _CheckStdout:
    report: RenderedReport = render_check_result(
        result=result,
        tree=tree,
        use_color=use_color,
        show_warnings=show_warnings,
    )
    return _CheckStdout(text=f"{report.text}\n", fault_count=report.fault_count)
