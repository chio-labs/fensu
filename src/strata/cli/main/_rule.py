"""Run the strata rule-inspection command."""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path
from typing import TextIO

from strata.cli.constants import NO_COLOR_ENVIRONMENT_VARIABLE
from strata.cli.types import ColorMode
from strata.config.exceptions import ConfigError
from strata.config.main.load_project_config import load_project_config
from strata.config.models import Config, LoadedConfig, RuleExceptionEntry
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import DiscoveredTree
from strata.evaluation.main.validate_rule_exceptions import validate_rule_exceptions
from strata.reporting.constants import ANSI_BOLD_CYAN, ANSI_DIM, ANSI_RESET, REPORT_LINE_WIDTH
from strata.rules.authoring.main.is_rule_code import is_rule_code
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
    try:
        loaded: LoadedConfig = load_project_config(Path.cwd())
        project_dir: Path = loaded.source.path.parent.resolve()
        config: Config = loaded.config
        catalogue: tuple[RuleSpec, ...] = build_catalogue(config=config, repo_root=project_dir)
        tree: DiscoveredTree = discover_files(config=config, repo_root=project_dir)
        validate_rule_exceptions(config=config, repo_root=tree.repo_root.path)
    except ConfigError as error:
        stderr.write(f"{error}\n")
        return 2
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in catalogue}
    rule: RuleSpec | None = rules_by_code.get(args.code) if is_rule_code(args.code) else None
    if rule is None:
        stderr.write(f"Unknown rule code: {args.code}\n")
        return 2
    use_color: bool = NO_COLOR_ENVIRONMENT_VARIABLE not in os.environ and (
        args.color == ColorMode.ALWAYS or (args.color == ColorMode.AUTO and stdout.isatty())
    )
    exceptions: tuple[RuleExceptionEntry, ...] = tuple(
        exception for exception in config.rule_exceptions if exception.rule == rule.code
    )
    stdout.write(_render_rule(rule=rule, exceptions=exceptions, use_color=use_color))
    stdout.write("\n")
    return 0


def _render_rule(
    *, rule: RuleSpec, exceptions: tuple[RuleExceptionEntry, ...], use_color: bool
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
            scope: str = ", ".join(exception.symbols) if exception.symbols else "file-level"
            lines.append(f"  {exception.path}: {scope}")
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
