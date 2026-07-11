"""Run the strata check command."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import TextIO

from strata.config.core.exceptions import ConfigError
from strata.config.core.main.load_project_config import load_project_config
from strata.config.core.models import Config, LoadedConfig
from strata.discovery.core.main.discover_files import discover_files
from strata.discovery.core.models import DiscoveredTree
from strata.evaluation.core.main.evaluate import evaluate
from strata.evaluation.core.main.validate_rule_exceptions import validate_rule_exceptions
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
    invocation_dir: Path = Path.cwd().resolve()
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
        tree: DiscoveredTree = discover_files(config, repo_root=project_dir)
        ruleset: tuple[RuleSpec, ...] = build_ruleset(config, repo_root=project_dir)
        validate_rule_exceptions(config=config, repo_root=tree.repo_root.path)
        result: EvaluationResult = evaluate(tree=tree, ruleset=ruleset, config=config)
    except ConfigError as error:
        stderr.write(f"{error}\n")
        return 2
    report: RenderedReport = render(
        faults=result.faults,
        root=tree.repo_root.path,
        use_color=not args.no_color and stdout.isatty(),
        applied_exception_count=result.applied_exception_count,
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


def _invocation_path(*, value: str, invocation_dir: Path) -> str:
    path: Path = Path(value)
    return str(path.resolve() if path.is_absolute() else (invocation_dir / path).resolve())
