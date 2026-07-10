"""Run the strata rule-inspection command."""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path
from typing import TextIO

from strata.cli.core.constants import NO_COLOR_ENVIRONMENT_VARIABLE
from strata.cli.core.types import ColorMode
from strata.config.core.main.load_config import load_config
from strata.config.core.models import Config, RuleExceptionEntry
from strata.discovery.core.main.discover_files import discover_files
from strata.discovery.core.models import DiscoveredTree
from strata.evaluation.core.main.validate_rule_exceptions import validate_rule_exceptions
from strata.reporting.core.constants import ANSI_BOLD_CYAN, ANSI_DIM, ANSI_RESET, REPORT_LINE_WIDTH
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.main.build_catalogue import build_catalogue


def run_rule(
    *,
    argv: tuple[str, ...] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Render metadata for one rule code."""

    args: argparse.Namespace = _parser().parse_args(() if argv is None else argv)
    config: Config = load_config(Path.cwd())
    catalogue: tuple[RuleSpec, ...] = build_catalogue(config)
    tree: DiscoveredTree = discover_files(config)
    validate_rule_exceptions(config=config, repo_root=tree.repo_root.path)
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in catalogue}
    rule: RuleSpec | None = rules_by_code.get(args.code.upper())
    if rule is None:
        stderr.write(f"Unknown rule code: {args.code}\n")
        return 2
    use_color: bool = NO_COLOR_ENVIRONMENT_VARIABLE not in os.environ and (
        args.color == ColorMode.ALWAYS or (args.color == ColorMode.AUTO and stdout.isatty())
    )
    exceptions: tuple[RuleExceptionEntry, ...] = tuple(
        exception for exception in config.rule_exceptions if exception.rule == rule.code
    )
    stdout.write(_render_rule(rule, exceptions=exceptions, use_color=use_color))
    stdout.write("\n")
    return 0


def _render_rule(
    rule: RuleSpec, *, exceptions: tuple[RuleExceptionEntry, ...], use_color: bool
) -> str:
    remediation: str = rule.remediation or "None provided."
    source: str = rule.source or "core"
    enabled: str = "yes" if rule.enabled_by_default else "no"
    header: str = f"{rule.code} {rule.slug}"
    if use_color:
        header = f"{ANSI_BOLD_CYAN}{rule.code}{ANSI_RESET} {rule.slug}"
    fields: tuple[tuple[str, str], ...] = (
        ("Family", rule.family.value),
        ("Severity", rule.severity.value),
        ("Kind", rule.kind.value),
        ("Enabled by default", enabled),
        ("Source", source),
        ("Message", rule.message),
        ("Remediation", remediation),
    )
    lines: list[str] = [header]
    for label, value in fields:
        prefix: str = f"{label}: "
        wrapped: list[str] = textwrap.wrap(
            value,
            width=REPORT_LINE_WIDTH,
            initial_indent=prefix,
            subsequent_indent=" " * len(prefix),
        )
        if use_color:
            first_value: str = wrapped[0].removeprefix(prefix)
            wrapped[0] = f"{ANSI_DIM}{label}:{ANSI_RESET} {first_value}"
        lines.extend(wrapped)
    if exceptions:
        lines.extend(("", "Active exceptions:"))
        for exception in exceptions:
            symbols: str = ", ".join(exception.symbols)
            lines.append(f"  {exception.path}: {symbols}")
            lines.append(f"    Reason: {exception.reason}")
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="strata rule")
    parser.add_argument("code", help="rule code to inspect")
    parser.add_argument(
        "--color",
        choices=tuple(ColorMode),
        default=ColorMode.AUTO,
        help="ANSI color behavior",
    )
    return parser
