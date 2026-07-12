"""Run the strata check command."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import TextIO

from strata.cache.fingerprints.main.build_global import build_global_fingerprint
from strata.cache.fingerprints.models import GlobalFingerprintBuild
from strata.cache.results.main.evaluate import evaluate_with_cache
from strata.cache.results.models import CacheEvaluation, CacheStats
from strata.cli.helpers.check_reporting import render_check_result
from strata.cli.main.cache_status import write_cache_status
from strata.config.exceptions import ConfigError
from strata.config.main.load_project_config import load_project_config
from strata.config.models import Config, LoadedConfig
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import DiscoveredTree
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.main.validate_rule_exceptions import validate_rule_exceptions
from strata.evaluation.models import EvaluationResult
from strata.reporting.models import RenderedReport
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.main.build_ruleset import build_ruleset


def run_check(
    *,
    argv: tuple[str, ...] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Run `strata check` and return its process exit code."""

    args: argparse.Namespace = _parser().parse_args(() if argv is None else argv)
    invocation_dir: Path = Path.cwd().resolve()
    cache_stats: CacheStats | None = None
    cache_disabled_reason: str | None = None
    try:
        loaded: LoadedConfig = load_project_config(invocation_dir)
        project_dir: Path = loaded.source.path.parent.resolve()
        config: Config = loaded.config
        if args.paths:
            config = replace(
                config,
                roots=tuple(
                    _invocation_path(value=value, invocation_dir=invocation_dir)
                    for value in args.paths
                ),
            )
        if args.cache_enabled is not None:
            config = replace(
                config,
                cache=replace(config.cache, enabled=args.cache_enabled),
            )
        tree: DiscoveredTree = discover_files(config=config, repo_root=project_dir)
        ruleset: tuple[RuleSpec, ...] = build_ruleset(config=config, repo_root=project_dir)
        validate_rule_exceptions(config=config, repo_root=tree.repo_root.path)
        fingerprint_build: GlobalFingerprintBuild | None = (
            build_global_fingerprint(config=config, ruleset=ruleset, repo_root=project_dir)
            if config.cache.enabled
            else None
        )
        if fingerprint_build is not None:
            cache_disabled_reason = fingerprint_build.disabled_reason
        if fingerprint_build is None or fingerprint_build.fingerprint is None:
            result: EvaluationResult = evaluate(tree=tree, ruleset=ruleset, config=config)
        else:
            cached: CacheEvaluation = evaluate_with_cache(
                tree=tree,
                ruleset=ruleset,
                config=config,
                global_fingerprint=fingerprint_build.fingerprint,
            )
            result = cached.result
            cache_stats = cached.stats
    except ConfigError as error:
        stderr.write(f"{error}\n")
        return 2
    report: RenderedReport = render_check_result(
        result=result,
        tree=tree,
        use_color=not args.no_color and stdout.isatty(),
    )
    write_cache_status(
        stderr=stderr,
        stats=cache_stats,
        show_stats=args.cache_stats,
        disabled_reason=cache_disabled_reason,
    )
    if result.selection is not None and result.selection.filtered:
        stdout.write(
            f"Evaluation: "
            f"{result.selection.discovered_count - result.selection.excluded_count:,} of "
            f"{result.selection.discovered_count:,} Python files "
            f"({result.selection.excluded_count:,} excluded by config)\n"
        )
    stdout.write(report.text)
    stdout.write("\n")
    return 1 if report.fault_count else 0


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="strata check")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI color output")
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


def _invocation_path(*, value: str, invocation_dir: Path) -> str:
    path: Path = Path(value)
    return str(path.resolve() if path.is_absolute() else (invocation_dir / path).resolve())
