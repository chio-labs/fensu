"""Run the strata rule-inspection command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from strata.config.core.main.load_config import load_config
from strata.config.core.models import Config
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
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in build_catalogue(config)}
    rule: RuleSpec | None = rules_by_code.get(args.code.upper())
    if rule is None:
        stderr.write(f"Unknown rule code: {args.code}\n")
        return 2
    stdout.write(_render_rule(rule))
    stdout.write("\n")
    return 0


def _render_rule(rule: RuleSpec) -> str:
    remediation: str = rule.remediation or "None provided."
    source: str = rule.source or "core"
    enabled: str = "yes" if rule.enabled_by_default else "no"
    return "\n".join(
        (
            f"{rule.code} {rule.slug}",
            f"Family: {rule.family.value}",
            f"Severity: {rule.severity.value}",
            f"Kind: {rule.kind.value}",
            f"Enabled by default: {enabled}",
            f"Source: {source}",
            f"Message: {rule.message}",
            f"Remediation: {remediation}",
        )
    )


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="strata rule")
    parser.add_argument("code", help="rule code to inspect")
    return parser
