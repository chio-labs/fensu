"""Execute one configured check command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from fensu.analysis.main.resolve_native_backend_version import resolve_native_backend_version
from fensu.cli._helpers.check_evaluation import evaluated_check
from fensu.cli._helpers.check_output import write_memory_check_result
from fensu.cli._helpers.check_reporting import skill_freshness_footer, write_check_diagnostics
from fensu.cli._helpers.check_setup import prepare_check_inputs
from fensu.cli.exceptions import CliCommandError
from fensu.config.exceptions import ConfigError

if TYPE_CHECKING:
    from fensu.cache.fingerprints.models import CacheFingerprint
    from fensu.cli.models import CheckEvaluation, CheckInputs
    from fensu.config.models import LoadedConfig
    from fensu.discovery.models import DiscoveredTree
    from fensu.evaluation.models import EvaluationResult
    from fensu.rules.catalog.models import RuleSelection


def execute_check(
    *,
    argv: tuple[str, ...] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Execute `fensu check` and return its process exit code."""

    args: argparse.Namespace = _parser().parse_args(() if argv is None else argv)
    invocation_dir: Path = Path.cwd().resolve()
    use_color: bool = not args.no_color and stdout.isatty()
    _ = resolve_native_backend_version()
    try:
        inputs: CheckInputs = prepare_check_inputs(args=args, invocation_dir=invocation_dir)
        loaded: LoadedConfig = inputs.loaded
        project_dir: Path = inputs.project_dir
        rule_selection: RuleSelection = inputs.rule_selection
        tree: DiscoveredTree = inputs.tree
        evaluation: CheckEvaluation = evaluated_check(
            tree=tree,
            config=inputs.config,
            rule_selection=rule_selection,
            project_dir=project_dir,
            warn=args.warn,
            jobs=args.jobs,
        )
    except (CliCommandError, ConfigError) as error:
        stderr.write(f"{error}\n")
        return 2
    write_check_diagnostics(
        loaded=loaded,
        selection=rule_selection,
        stderr=stderr,
        stats=evaluation.stats,
        show_stats=args.cache_stats,
        disabled_reason=evaluation.disabled_reason,
    )
    freshness_footer: str = skill_freshness_footer(
        loaded=loaded,
        selection=rule_selection,
        project_root=project_dir,
        invocation_root=invocation_dir,
        use_color=not args.no_color and stderr.isatty(),
    )
    if evaluation.short_circuit is not None:
        stdout.write(
            evaluation.short_circuit.color_output
            if use_color
            else evaluation.short_circuit.plain_output
        )
        memory_fault_count: int = write_memory_check_result(
            stdout=stdout,
            result=inputs.memory_result,
            use_color=use_color,
        )
        stderr.write(freshness_footer)
        return 1 if evaluation.short_circuit.exit_code or memory_fault_count else 0
    result: EvaluationResult | None = evaluation.result
    if result is None:
        stderr.write("Cached evaluation returned no result.\n")
        return 2
    from fensu.cli._helpers.check_output import check_stdout_text, persist_check_output

    text, fault_count = check_stdout_text(
        result=result,
        tree=tree,
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
            repo_root=project_dir,
            global_fingerprint=global_fingerprint,
            targets=surface_targets,
            result=result,
            tree=tree,
            show_warnings=args.warn,
            selected_output=text,
            selected_fault_count=fault_count,
            selected_use_color=use_color,
            expected_index_fingerprint=surface_index_fingerprint,
        )
    stdout.write(text)
    memory_fault_count = write_memory_check_result(
        stdout=stdout,
        result=inputs.memory_result,
        use_color=use_color,
    )
    stderr.write(freshness_footer)
    return 1 if fault_count or memory_fault_count else 0


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="fensu check")
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
    parser.add_argument("paths", nargs="*", help="configured root paths to check")
    return parser


def _positive_int(value: str) -> int:
    parsed: int = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("jobs must be at least 1")
    return parsed
