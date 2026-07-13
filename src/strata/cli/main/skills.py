"""Install or update repository-aware Strata skills."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from strata.agentdocs.exceptions import SkillInstallError
from strata.agentdocs.main.build_generation_context import build_generation_context
from strata.agentdocs.main.build_install_plan import build_install_plan
from strata.agentdocs.main.check_install import check_skill_install
from strata.agentdocs.main.update import update_skills
from strata.agentdocs.models import (
    SkillFreshnessResult,
    SkillGenerationContext,
    SkillInstallPlan,
    SkillUpdateResult,
)
from strata.agentdocs.types import SkillCommand, SkillFreshnessReason, SkillTarget
from strata.cli.constants import SKILLS_UPDATE_OPTION
from strata.config.exceptions import ConfigError
from strata.config.main.load_project_config import load_project_config
from strata.config.models import Config, LoadedConfig
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import DiscoveredTree
from strata.evaluation.main.validate_rule_exceptions import validate_rule_exceptions
from strata.rules.catalog.main.build_check_rule_selection import build_check_rule_selection
from strata.rules.catalog.models import RuleSelection


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
    if args.global_install and args.install_root is not None:
        stderr.write("--install-root cannot be combined with --global.\n")
        return 2
    if args.check and args.force:
        stderr.write("--check cannot be combined with --force.\n")
        return 2
    requested_targets: tuple[SkillTarget, ...] = tuple(
        SkillTarget(target) for target in args.targets
    )
    try:
        command_result: SkillFreshnessResult | SkillUpdateResult = _execute_skills(
            args=args,
            requested_targets=requested_targets,
            home_dir=home_dir,
        )
    except (ConfigError, SkillInstallError, OSError) as error:
        stderr.write(f"{error}\n")
        return 2
    if isinstance(command_result, SkillFreshnessResult):
        if command_result.issues:
            stdout.write("Strata skill files require update:\n")
            for issue in command_result.issues:
                stdout.write(f"  {issue.path}: {issue.reason.value}\n")
            collision: bool = any(
                issue.reason is SkillFreshnessReason.COLLISION for issue in command_result.issues
            )
            return 2 if collision else 1
        stdout.write("Strata skill files are current:\n")
        for inspected_path in command_result.inspected_paths:
            stdout.write(f"  {inspected_path}\n")
        return 0
    stdout.write("Updated Strata skill files:\n")
    for written_path in command_result.written_paths:
        stdout.write(f"  {written_path}\n")
    return 0


def _execute_skills(
    *,
    args: argparse.Namespace,
    requested_targets: tuple[SkillTarget, ...],
    home_dir: Path | None,
) -> SkillFreshnessResult | SkillUpdateResult:
    loaded: LoadedConfig = load_project_config(Path.cwd())
    project_dir: Path = loaded.source.path.parent.resolve()
    config: Config = loaded.config
    selection: RuleSelection = build_check_rule_selection(
        config=config, repo_root=project_dir, include_warnings=True
    )
    tree: DiscoveredTree = discover_files(config=config, repo_root=project_dir)
    validate_rule_exceptions(config=config, repo_root=tree.repo_root.path)
    context: SkillGenerationContext = build_generation_context(
        config=config,
        source=loaded.source,
        project_root=project_dir,
        selection=selection,
        install_root=args.install_root,
        invocation_root=Path.cwd(),
    )
    if args.check:
        plan: SkillInstallPlan = build_install_plan(
            context=context,
            global_install=args.global_install,
            requested_targets=requested_targets,
            home_dir=home_dir,
        )
        return check_skill_install(plan=plan, authoritative=True)
    return update_skills(
        context=context,
        global_install=args.global_install,
        requested_targets=requested_targets,
        force=args.force,
        home_dir=home_dir,
    )


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
    update_parser.add_argument(
        "--check",
        action="store_true",
        help="verify deterministic installed bytes without writing files",
    )
    update_parser.add_argument(
        "--install-root",
        metavar="git|project|PATH",
        help="install locally at the Git root, project root, or an explicit path",
    )
    return parser
