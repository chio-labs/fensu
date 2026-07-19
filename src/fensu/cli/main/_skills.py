"""Install or update repository-aware Fensu skills."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from fensu.agentdocs.exceptions import SkillInstallError
from fensu.agentdocs.main.build_generation_context import build_generation_context
from fensu.agentdocs.main.build_install_plan import build_install_plan
from fensu.agentdocs.main.check_install import check_skill_install
from fensu.agentdocs.main.discover_project_skills import discover_project_skills
from fensu.agentdocs.main.update import update_skills
from fensu.agentdocs.models import (
    ProjectSkillBundle,
    SkillFreshnessResult,
    SkillGenerationContext,
    SkillInstallPlan,
    SkillUpdateResult,
)
from fensu.agentdocs.types import SkillFreshnessReason, SkillTarget
from fensu.config.exceptions import ConfigError
from fensu.config.main.load_project_config import load_project_config
from fensu.config.models import Config, LoadedConfig
from fensu.discovery.main.discover_files import discover_files
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation.main.validate_rule_exceptions import validate_rule_exceptions
from fensu.rules.catalog.main.build_check_rule_selection import build_check_rule_selection
from fensu.rules.catalog.models import RuleSelection


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
    args: argparse.Namespace = parser.parse_args(command_args)
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
            stdout.write("Fensu skill files require update:\n")
            for issue in command_result.issues:
                stdout.write(f"  {issue.path.as_posix()}: {issue.reason.value}\n")
            collision: bool = any(
                issue.reason is SkillFreshnessReason.COLLISION for issue in command_result.issues
            )
            return 2 if collision else 1
        stdout.write("Fensu skill files are current:\n")
        for inspected_path in command_result.inspected_paths:
            stdout.write(f"  {inspected_path.as_posix()}\n")
        return 0
    stdout.write("Updated Fensu skill files:\n")
    for written_path in command_result.written_paths:
        stdout.write(f"  {written_path.as_posix()}\n")
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
    project_bundles: tuple[ProjectSkillBundle, ...] = discover_project_skills(
        project_root=project_dir,
        generated_identity=context.identity,
    )
    if args.check:
        plan: SkillInstallPlan = build_install_plan(
            context=context,
            global_install=args.global_install,
            requested_targets=requested_targets,
            home_dir=home_dir,
            project_bundles=project_bundles,
        )
        return check_skill_install(plan=plan, authoritative=True)
    return update_skills(
        context=context,
        global_install=args.global_install,
        requested_targets=requested_targets,
        force=args.force,
        home_dir=home_dir,
        project_bundles=project_bundles,
    )


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="fensu skills")
    parser.add_argument("--global", dest="global_install", action="store_true")
    parser.add_argument(
        "--target",
        dest="targets",
        action="append",
        choices=tuple(SkillTarget),
        default=[],
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify deterministic installed bytes without writing files",
    )
    parser.add_argument(
        "--install-root",
        metavar="git|project|PATH",
        help="install locally at the Git root, project root, or an explicit path",
    )
    return parser
