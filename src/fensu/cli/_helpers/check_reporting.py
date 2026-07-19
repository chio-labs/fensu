"""Assemble the rendered check report and threshold observations."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from fensu.cache.results.models import CacheStats
from fensu.cli._helpers.skill_freshness import installed_skill_is_stale
from fensu.cli.main._cache_status import write_cache_status
from fensu.config.models import LoadedConfig
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation.models import EvaluationResult, EvaluationSelection
from fensu.reporting.classes.cli_style import CliStyle
from fensu.reporting.main.render import render
from fensu.reporting.models import RenderedReport
from fensu.rules.catalog.main.undeclared_cacheable import undeclared_cacheable_codes
from fensu.rules.catalog.models import RuleSelection


def write_check_diagnostics(
    *,
    loaded: LoadedConfig,
    selection: RuleSelection,
    stderr: TextIO,
    stats: CacheStats | None,
    show_stats: bool,
    disabled_reason: str | None,
) -> None:
    """Write cache diagnostics to stderr."""

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


def skill_freshness_footer(
    *,
    loaded: LoadedConfig,
    selection: RuleSelection,
    project_root: Path,
    invocation_root: Path,
    use_color: bool,
) -> str:
    """Return a final actionable notice when installed skill files are stale."""

    if not installed_skill_is_stale(
        loaded=loaded,
        selection=selection,
        project_root=project_root,
        invocation_root=invocation_root,
    ):
        return ""
    style: CliStyle = CliStyle(use_color=use_color)
    return (
        f"\n{style.warning('Fensu skill files are out of date')}\n"
        f"  Run: {style.link('fensu skills')}\n"
    )


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
        evaluation_summary=_evaluation_summary(result=result),
        applied_exception_count=result.applied_exception_count,
        threshold_override_uses=result.threshold_override_uses,
    )


def _evaluation_summary(*, result: EvaluationResult) -> str | None:
    selection: EvaluationSelection | None = result.selection
    if selection is None or not selection.filtered:
        return None
    return (
        "Evaluation: "
        f"{selection.discovered_count - selection.excluded_count:,} of "
        f"{selection.discovered_count:,} Python files "
        f"({selection.excluded_count:,} excluded by config)"
    )
