"""Run the strata check command."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import TextIO

from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.models import FactBackendSelection
from strata.cli._helpers.check_evaluation import evaluated_check
from strata.cli._helpers.check_output import check_stdout_text, persist_check_output
from strata.cli._helpers.check_paths import invocation_path
from strata.cli._helpers.check_reporting import skill_freshness_footer, write_check_diagnostics
from strata.cli.models import CheckEvaluation
from strata.config.exceptions import ConfigError
from strata.config.main.load_project_config import load_project_config
from strata.config.models import Config, LoadedConfig
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import DiscoveredTree
from strata.evaluation.main.validate_rule_exceptions import validate_rule_exceptions
from strata.rules.catalog.main.build_check_rule_selection import build_check_rule_selection
from strata.rules.catalog.models import RuleSelection


def run_check(
    *,
    argv: tuple[str, ...] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Run `strata check` and return its process exit code."""

    args: argparse.Namespace = _parser().parse_args(() if argv is None else argv)
    invocation_dir: Path = Path.cwd().resolve()
    use_color: bool = not args.no_color and stdout.isatty()
    selection: FactBackendSelection = select_fact_backend()
    if selection.warning is not None:
        stderr.write(f"{selection.warning}\n")
    try:
        loaded: LoadedConfig = load_project_config(invocation_dir)
        project_dir: Path = loaded.source.path.parent.resolve()
        rule_selection: RuleSelection = build_check_rule_selection(
            config=loaded.config,
            repo_root=project_dir,
            include_warnings=args.warn,
        )
        config: Config = _configured(args=args, loaded=loaded, invocation_dir=invocation_dir)
        tree: DiscoveredTree = discover_files(config=config, repo_root=project_dir)
        validate_rule_exceptions(config=config, repo_root=tree.repo_root.path)
        evaluation: CheckEvaluation = evaluated_check(
            tree=tree,
            config=config,
            rule_selection=rule_selection,
            project_dir=project_dir,
            warn=args.warn,
        )
    except ConfigError as error:
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
        stderr.write(freshness_footer)
        return evaluation.short_circuit.exit_code
    if evaluation.result is None:
        stderr.write("Cached evaluation returned no result.\n")
        return 2
    text, fault_count = check_stdout_text(
        result=evaluation.result,
        tree=tree,
        use_color=use_color,
        show_warnings=args.warn,
    )
    if (
        evaluation.surface_targets is not None
        and evaluation.global_fingerprint is not None
        and evaluation.surface_index_fingerprint is not None
    ):
        _ = persist_check_output(
            repo_root=project_dir,
            global_fingerprint=evaluation.global_fingerprint,
            targets=evaluation.surface_targets,
            result=evaluation.result,
            tree=tree,
            show_warnings=args.warn,
            selected_output=text,
            selected_fault_count=fault_count,
            selected_use_color=use_color,
            expected_index_fingerprint=evaluation.surface_index_fingerprint,
        )
    stdout.write(text)
    stderr.write(freshness_footer)
    return 1 if fault_count else 0


def _configured(
    *,
    args: argparse.Namespace,
    loaded: LoadedConfig,
    invocation_dir: Path,
) -> Config:
    config: Config = loaded.config
    if args.paths:
        config = replace(
            config,
            roots=tuple(
                invocation_path(value=value, invocation_dir=invocation_dir) for value in args.paths
            ),
        )
    if args.cache_enabled is not None:
        config = replace(
            config,
            cache=replace(config.cache, enabled=args.cache_enabled),
        )
    return config


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="strata check")
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
    parser.add_argument("paths", nargs="*", help="configured root paths to check")
    return parser
