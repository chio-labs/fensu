"""Assemble the rendered check report and threshold observations."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from strata.cache.results.models import CacheStats
from strata.cli._helpers.skill_freshness import installed_skill_is_stale
from strata.cli.main.cache_status import write_cache_status
from strata.config.models import LoadedConfig
from strata.discovery.models import DiscoveredTree
from strata.evaluation.models import EvaluationResult
from strata.reporting.main.render import render
from strata.reporting.models import RenderedReport
from strata.rules.catalog.main.undeclared_cacheable import undeclared_cacheable_codes
from strata.rules.catalog.models import RuleSelection


def write_check_diagnostics(
    *,
    loaded: LoadedConfig,
    selection: RuleSelection,
    project_root: Path,
    invocation_root: Path,
    stderr: TextIO,
    stats: CacheStats | None,
    show_stats: bool,
    disabled_reason: str | None,
) -> None:
    """Write cache status and skill freshness diagnostics to stderr."""

    write_cache_status(
        stderr=stderr,
        stats=stats,
        show_stats=show_stats,
        disabled_reason=disabled_reason,
    )
    if stats is not None:
        undeclared: tuple[str, ...] = undeclared_cacheable_codes(
            rules=(*selection.blocking, *selection.warnings),
            allowed_packages=frozenset(
                name.partition(".")[0] for name in loaded.config.rule_modules
            ),
        )
        if undeclared:
            stderr.write(
                "Custom rules appear cacheable; declare cacheable=True to enable "
                f"caching for them: {', '.join(undeclared)}\n"
            )
    if installed_skill_is_stale(
        loaded=loaded,
        selection=selection,
        project_root=project_root,
        invocation_root=invocation_root,
    ):
        stderr.write("Strata skill files are out of date; run `strata skills`.\n")


def render_check_result(
    *, result: EvaluationResult, tree: DiscoveredTree, use_color: bool, show_warnings: bool = False
) -> RenderedReport:
    """Render check faults with effective threshold-override observations."""

    return render(
        faults=result.faults,
        warnings=result.warnings,
        root=tree.repo_root.path,
        use_color=use_color,
        show_warnings=show_warnings,
        applied_exception_count=result.applied_exception_count,
        threshold_override_uses=result.threshold_override_uses,
    )
