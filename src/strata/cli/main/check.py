"""Run the strata check command."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import TextIO

from strata.config.core.main.load_config import load_config
from strata.config.core.models import Config
from strata.discovery.core.main.discover_files import discover_files
from strata.discovery.core.models import DiscoveredTree
from strata.evaluation.core.main.evaluate import evaluate
from strata.evaluation.core.models import EvaluationResult
from strata.reporting.core.main.render import render
from strata.reporting.core.models import RenderedReport
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
    config: Config = load_config(Path.cwd())
    if args.paths:
        config = replace(config, roots=tuple(args.paths))
    tree: DiscoveredTree = discover_files(config)
    ruleset: tuple[RuleSpec, ...] = build_ruleset(config)
    result: EvaluationResult = evaluate(tree=tree, ruleset=ruleset, config=config)
    report: RenderedReport = render(
        faults=result.faults,
        root=tree.repo_root.path,
        use_color=not args.no_color and stdout.isatty(),
    )
    stderr.flush()
    stdout.write(report.text)
    stdout.write("\n")
    return 1 if report.fault_count else 0


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="strata check")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI color output")
    parser.add_argument("paths", nargs="*", help="configured root paths to check")
    return parser
