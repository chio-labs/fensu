"""Install or update repository-aware Strata skills."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from strata.agentdocs.core.exceptions import SkillInstallError
from strata.agentdocs.core.main.update import update_skills
from strata.agentdocs.core.models import SkillUpdateResult
from strata.agentdocs.core.types import SkillTarget
from strata.config.core.main.load_config import load_config
from strata.config.core.models import Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.main.build_ruleset import build_ruleset


def run_skills(
    *,
    argv: tuple[str, ...] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    home_dir: Path | None = None,
) -> int:
    """Generate and install skill files from the active repository rules."""

    args: argparse.Namespace = _parser().parse_args(() if argv is None else argv)
    project_dir: Path = Path.cwd()
    config: Config = load_config(project_dir)
    rules: tuple[RuleSpec, ...] = build_ruleset(config)
    requested_targets: tuple[SkillTarget, ...] = tuple(
        SkillTarget(target) for target in args.targets
    )
    try:
        result: SkillUpdateResult = update_skills(
            rules=rules,
            project_dir=project_dir,
            global_install=args.global_install,
            requested_targets=requested_targets,
            force=args.force,
            home_dir=home_dir,
        )
    except SkillInstallError as error:
        stderr.write(f"{error}\n")
        return 2
    stdout.write("Updated Strata skill files:\n")
    for written_path in result.written_paths:
        stdout.write(f"  {written_path}\n")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="strata skills")
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(
        dest="skills_command", required=True
    )
    update_parser: argparse.ArgumentParser = subparsers.add_parser("update")
    update_parser.add_argument("--global", dest="global_install", action="store_true")
    update_parser.add_argument(
        "--target",
        dest="targets",
        action="append",
        choices=tuple(SkillTarget),
        default=[],
    )
    update_parser.add_argument("--force", action="store_true")
    return parser
