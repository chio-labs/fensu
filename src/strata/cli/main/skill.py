"""Run the strata skill-generation command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from strata.agentdocs.core.main.generate import generate_skill
from strata.config.core.main.load_config import load_config
from strata.config.core.models import Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.main.build_ruleset import build_ruleset


def run_skill(
    *,
    argv: tuple[str, ...] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Generate agent guidance from the active project rules."""

    args: argparse.Namespace = _parser().parse_args(() if argv is None else argv)
    config: Config = load_config(Path.cwd())
    rules: tuple[RuleSpec, ...] = build_ruleset(config)
    document: str = generate_skill(rules=rules)
    if args.output is None:
        stdout.write(document)
        return 0
    output_path: Path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    stderr.write(f"Wrote {output_path}\n")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="strata skill")
    parser.add_argument("--output", help="write generated guidance to this path")
    return parser
