"""Install or update repository-aware Strata skills."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from strata.agentdocs.core.exceptions import SkillInstallError
from strata.agentdocs.core.main.update import update_skills
from strata.agentdocs.core.models import SkillUpdateResult
from strata.agentdocs.core.types import SkillCommand, SkillTarget
from strata.cli.core.constants import SKILLS_UPDATE_OPTION
from strata.config.core.exceptions import ConfigError
from strata.config.core.main.load_project_config import load_project_config
from strata.config.core.models import Config, LoadedConfig
from strata.discovery.core.main.discover_files import discover_files
from strata.discovery.core.models import DiscoveredTree
from strata.evaluation.core.main.validate_rule_exceptions import validate_rule_exceptions
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

    command_args: tuple[str, ...] = () if argv is None else argv
    parser: argparse.ArgumentParser = _parser()
    if command_args and command_args[0] == SKILLS_UPDATE_OPTION:
        stderr.write("`update` is a subcommand, not an option. Run `strata skills update`.\n")
        return 2
    args: argparse.Namespace = parser.parse_args(command_args)
    if args.skills_command is None:
        stderr.write(
            "A skills command is required. Run `strata skills update` to generate files.\n\n"
        )
        parser.print_help(file=stderr)
        return 2
    requested_targets: tuple[SkillTarget, ...] = tuple(
        SkillTarget(target) for target in args.targets
    )
    try:
        loaded: LoadedConfig = load_project_config(Path.cwd())
        project_dir: Path = loaded.source.path.parent.resolve()
        config: Config = loaded.config
        rules: tuple[RuleSpec, ...] = build_ruleset(config, repo_root=project_dir)
        tree: DiscoveredTree = discover_files(config, repo_root=project_dir)
        validate_rule_exceptions(config=config, repo_root=tree.repo_root.path)
        result: SkillUpdateResult = update_skills(
            config=config,
            rules=rules,
            project_dir=project_dir,
            global_install=args.global_install,
            requested_targets=requested_targets,
            force=args.force,
            home_dir=home_dir,
        )
    except (ConfigError, SkillInstallError) as error:
        stderr.write(f"{error}\n")
        return 2
    stdout.write("Updated Strata skill files:\n")
    for written_path in result.written_paths:
        stdout.write(f"  {written_path}\n")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="strata skills")
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(
        dest="skills_command"
    )
    update_parser: argparse.ArgumentParser = subparsers.add_parser(SkillCommand.UPDATE)
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
