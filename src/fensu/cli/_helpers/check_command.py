"""Execute one configured check command."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from fensu.analysis.main.resolve_native_backend_version import resolve_native_backend_version
from fensu.cache.fingerprints.constants import NO_CACHEABLE_RULES_REASON
from fensu.cli._helpers.check_evaluation import evaluated_check
from fensu.cli._helpers.check_reporting import (
    cacheability_advice_codes,
    write_check_diagnostics,
)
from fensu.cli._helpers.check_setup import prepare_check_inputs
from fensu.cli.constants import (
    COLOR_ALWAYS,
    COLOR_AUTO,
    COLOR_NEVER,
    NO_COLOR_ENVIRONMENT_VARIABLE,
)
from fensu.cli.exceptions import CliCommandError
from fensu.config.exceptions import ConfigError
from fensu.config.main.load_project_target_names import load_project_target_names

if TYPE_CHECKING:
    from fensu.cache.fingerprints.models import CacheFingerprint
    from fensu.cache.results.models import CacheStats
    from fensu.cli.models import CheckEvaluation, CheckInputs
    from fensu.evaluation.models import EvaluationResult, ThresholdOverrideUse
    from fensu.reporting.models import RenderedReport
    from fensu.rules.authoring.models import Fault


@dataclass(frozen=True, slots=True)
class _TargetCheck:
    """Prepared and evaluated state for one selected analyzer target."""

    inputs: CheckInputs
    evaluation: CheckEvaluation


def execute_check(
    *,
    argv: tuple[str, ...] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Execute `fensu check` and return its process exit code."""

    args: argparse.Namespace = _parser().parse_args(() if argv is None else argv)
    invocation_dir: Path = Path.cwd().resolve()
    use_color: bool = _use_color(color=args.color, no_color=args.no_color, stdout=stdout)
    _ = resolve_native_backend_version()
    try:
        target_names: tuple[str | None, ...] = load_project_target_names(
            start=invocation_dir, target=args.target
        )
        if len(target_names) > 1 and args.paths:
            raise CliCommandError(
                "Positional paths require exactly one selected target; use --target TARGET."
            )
        inputs: tuple[CheckInputs, ...] = tuple(
            _prepare_target(args=args, invocation_dir=invocation_dir, target=target)
            for target in target_names
        )
        aggregate_cache_enabled: bool = all(item.config.cache.enabled for item in inputs)
        checks: tuple[_TargetCheck, ...] = tuple(
            _evaluate_target(
                args=args,
                inputs=_with_cache_enabled(
                    inputs=item,
                    enabled=(
                        aggregate_cache_enabled if len(inputs) > 1 else item.config.cache.enabled
                    ),
                ),
                allow_short_circuit=len(inputs) == 1,
                cache_storage_root=(
                    _target_cache_storage_root(inputs=item)
                    if len(inputs) > 1 and aggregate_cache_enabled
                    else None
                ),
            )
            for item in inputs
        )
    except (CliCommandError, ConfigError) as error:
        stderr.write(f"{error}\n")
        return 2
    if len(checks) == 1:
        return _write_single_check(
            check=checks[0],
            args=args,
            stdout=stdout,
            stderr=stderr,
            use_color=use_color,
        )
    return _write_aggregate_check(
        checks=checks, args=args, stdout=stdout, stderr=stderr, use_color=use_color
    )


def _prepare_target(
    *,
    args: argparse.Namespace,
    invocation_dir: Path,
    target: str | None,
) -> CheckInputs:
    target_args: argparse.Namespace = argparse.Namespace(**vars(args))
    target_args.target = target
    return prepare_check_inputs(args=target_args, invocation_dir=invocation_dir)


def _evaluate_target(
    *,
    args: argparse.Namespace,
    inputs: CheckInputs,
    allow_short_circuit: bool,
    cache_storage_root: Path | None,
) -> _TargetCheck:
    evaluation: CheckEvaluation = evaluated_check(
        tree=inputs.tree,
        config=inputs.config,
        rule_selection=inputs.rule_selection,
        project_dir=inputs.project_dir,
        warn=args.warn,
        allow_short_circuit=allow_short_circuit,
        cache_storage_root=cache_storage_root,
        jobs=args.jobs,
    )
    return _TargetCheck(inputs=inputs, evaluation=evaluation)


def _with_cache_enabled(*, inputs: CheckInputs, enabled: bool) -> CheckInputs:
    if inputs.config.cache.enabled is enabled:
        return inputs
    return replace(
        inputs,
        config=replace(inputs.config, cache=replace(inputs.config.cache, enabled=enabled)),
    )


def _target_cache_storage_root(*, inputs: CheckInputs) -> Path:
    target: str = inputs.config.target or ""
    framed: bytes = json.dumps(
        [inputs.config.analyzer.value, target, inputs.config.target_root],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode()
    identity: str = hashlib.sha256(framed).hexdigest()
    storage_root: Path = inputs.project_dir / ".fensu/cache/targets" / identity
    try:
        storage_root.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return storage_root


def _write_single_check(
    *,
    check: _TargetCheck,
    args: argparse.Namespace,
    stdout: TextIO,
    stderr: TextIO,
    use_color: bool,
) -> int:
    inputs: CheckInputs = check.inputs
    evaluation: CheckEvaluation = check.evaluation
    write_check_diagnostics(
        loaded=inputs.loaded,
        selection=inputs.rule_selection,
        stderr=stderr,
        stats=evaluation.stats,
        show_stats=args.cache_stats,
        disabled_reason=evaluation.disabled_reason,
    )
    if evaluation.short_circuit is not None:
        stdout.write(
            evaluation.short_circuit.color_output
            if use_color
            else evaluation.short_circuit.plain_output
        )
        return evaluation.short_circuit.exit_code
    result: EvaluationResult | None = evaluation.result
    if result is None:
        stderr.write("Cached evaluation returned no result.\n")
        return 2
    from fensu.cli._helpers.check_output import check_stdout_text, persist_check_output

    text, fault_count = check_stdout_text(
        result=result,
        tree=inputs.tree,
        use_color=use_color,
        show_warnings=args.warn,
    )
    surface_targets: tuple[str, ...] | None = evaluation.surface_targets
    global_fingerprint: CacheFingerprint | None = evaluation.global_fingerprint
    surface_index_fingerprint: CacheFingerprint | None = evaluation.surface_index_fingerprint
    if (
        surface_targets is not None
        and global_fingerprint is not None
        and surface_index_fingerprint is not None
    ):
        _ = persist_check_output(
            repo_root=inputs.project_dir,
            global_fingerprint=global_fingerprint,
            targets=surface_targets,
            result=result,
            tree=inputs.tree,
            show_warnings=args.warn,
            selected_output=text,
            selected_fault_count=fault_count,
            selected_use_color=use_color,
            expected_index_fingerprint=surface_index_fingerprint,
        )
    stdout.write(text)
    return 1 if fault_count else 0


def _write_aggregate_check(
    *,
    checks: tuple[_TargetCheck, ...],
    args: argparse.Namespace,
    stdout: TextIO,
    stderr: TextIO,
    use_color: bool,
) -> int:
    from fensu.cli.main._cache_status import write_cache_status
    from fensu.reporting.main.render import render

    _write_aggregate_cacheability_advice(checks=checks, stderr=stderr)
    stats: CacheStats | None = _combined_cache_stats(checks=checks)
    write_cache_status(
        stderr=stderr,
        stats=stats,
        show_stats=args.cache_stats,
        disabled_reason=_combined_disabled_reason(checks=checks),
    )
    results: tuple[EvaluationResult, ...] = tuple(
        check.evaluation.result for check in checks if check.evaluation.result is not None
    )
    if len(results) != len(checks):
        stderr.write("Cached evaluation returned no result.\n")
        return 2
    fault_items: list[Fault] = []
    warning_items: list[Fault] = []
    threshold_items: set[ThresholdOverrideUse] = set()
    selected: int = 0
    discovered: int = 0
    for result in results:
        fault_items.extend(result.faults)
        warning_items.extend(result.warnings)
        threshold_items.update(result.threshold_override_uses)
        if result.selection is not None:
            selected += result.selection.discovered_count - result.selection.excluded_count
            discovered += result.selection.discovered_count
    faults: tuple[Fault, ...] = tuple(sorted(fault_items, key=_fault_key))
    warnings: tuple[Fault, ...] = tuple(sorted(warning_items, key=_fault_key))
    threshold_uses: tuple[ThresholdOverrideUse, ...] = tuple(
        sorted(threshold_items, key=_threshold_use_key)
    )
    excluded: int = discovered - selected
    report: RenderedReport = render(
        faults=faults,
        warnings=warnings,
        root=checks[0].inputs.project_dir,
        use_color=use_color,
        show_warnings=args.warn,
        evaluation_summary=(
            f"Evaluation: {selected:,} of {discovered:,} Python files "
            f"({excluded:,} excluded by config)"
            if excluded
            else None
        ),
        applied_exception_count=sum(result.applied_exception_count for result in results),
        threshold_override_uses=threshold_uses,
    )
    stdout.write(f"{report.text}\n")
    return 1 if report.fault_count else 0


def _combined_cache_stats(*, checks: tuple[_TargetCheck, ...]) -> CacheStats | None:
    from fensu.cache.results.models import CacheStats

    values: tuple[CacheStats, ...] = tuple(
        check.evaluation.stats for check in checks if check.evaluation.stats is not None
    )
    non_cacheable: int = sum(_missing_non_cacheable_work(check=check) for check in checks)
    if not values and non_cacheable == 0:
        return None
    return CacheStats(
        hits=sum(value.hits for value in values),
        misses=sum(value.misses for value in values),
        invalidations=sum(value.invalidations for value in values),
        writes=sum(value.writes for value in values),
        non_cacheable=sum(value.non_cacheable for value in values) + non_cacheable,
        storage_failed=any(value.storage_failed for value in values),
        internal_error=any(value.internal_error for value in values),
    )


def _missing_non_cacheable_work(*, check: _TargetCheck) -> int:
    if (
        not check.inputs.config.cache.enabled
        or check.evaluation.stats is not None
        or check.evaluation.disabled_reason != NO_CACHEABLE_RULES_REASON
    ):
        return 0
    result: EvaluationResult | None = check.evaluation.result
    if result is None:
        return 0
    if result.file_evaluations:
        return len(result.file_evaluations)
    if result.selection is None:
        return 0
    return result.selection.discovered_count - result.selection.excluded_count


def _write_aggregate_cacheability_advice(
    *, checks: tuple[_TargetCheck, ...], stderr: TextIO
) -> None:
    grouped: dict[tuple[str, ...], list[str]] = {}
    for check in checks:
        codes: tuple[str, ...] = cacheability_advice_codes(
            loaded=check.inputs.loaded,
            selection=check.inputs.rule_selection,
            cache_attempted=check.inputs.config.cache.enabled,
        )
        if codes:
            target: str = check.inputs.config.target or "legacy"
            grouped.setdefault(codes, []).append(target)
    ordered: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
        (tuple(sorted(targets)), codes) for codes, targets in grouped.items()
    ]
    ordered.sort()
    for targets, codes in ordered:
        noun: str = "target" if len(targets) == 1 else "targets"
        stderr.write(
            f"Custom rules appear cacheable for {noun} {', '.join(targets)}; "
            "declare cacheable=True to enable caching for them: "
            f"{', '.join(codes)}\n"
        )


def _combined_disabled_reason(*, checks: tuple[_TargetCheck, ...]) -> str | None:
    reasons: list[str] = []
    for check in checks:
        reason: str | None = check.evaluation.disabled_reason
        if reason is not None and reason not in reasons:
            reasons.append(reason)
    return "; ".join(reasons) if reasons else None


def _fault_key(fault: Fault) -> tuple[str, int, int, str]:
    return (fault.path.as_posix(), fault.line or 0, fault.column or 0, fault.code)


def _threshold_use_key(use: ThresholdOverrideUse) -> tuple[str, str, int, str, int, str]:
    return (
        use.repository_path,
        use.threshold.value,
        use.effective_value,
        use.matched_pattern,
        use.override_order,
        use.reason,
    )


def _use_color(*, color: str, no_color: bool, stdout: TextIO) -> bool:
    if no_color or color == COLOR_NEVER or os.environ.get(NO_COLOR_ENVIRONMENT_VARIABLE):
        return False
    return color == COLOR_ALWAYS or stdout.isatty()


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="fensu check")
    parser.add_argument(
        "--color",
        choices=(COLOR_AUTO, COLOR_ALWAYS, COLOR_NEVER),
        default=COLOR_AUTO,
        help="ANSI color behavior",
    )
    parser.add_argument("--no-color", action="store_true", help="disable ANSI color output")
    parser.add_argument(
        "--warn",
        action="store_true",
        help="evaluate and report configured warning rules without making them blocking",
    )
    cache_options: argparse._MutuallyExclusiveGroup = parser.add_mutually_exclusive_group()
    cache_options.add_argument(
        "--cache",
        dest="cache_enabled",
        action="store_true",
        help="enable persistent result caching",
    )
    cache_options.add_argument(
        "--no-cache",
        dest="cache_enabled",
        action="store_false",
        help="disable persistent result caching",
    )
    parser.set_defaults(cache_enabled=None)
    parser.add_argument(
        "--cache-stats",
        action="store_true",
        help="write cache operation counts to stderr when caching is enabled",
    )
    parser.add_argument(
        "--jobs",
        type=_positive_int,
        default=None,
        help="worker processes for full evaluations (default: automatic)",
    )
    parser.add_argument("--target", metavar="TARGET", help="named analyzer target to check")
    parser.add_argument("paths", nargs="*", help="configured root paths to check")
    return parser


def _positive_int(value: str) -> int:
    parsed: int = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("jobs must be at least 1")
    return parsed
