"""Uncached evaluation and summarized starting-ruleset drift."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from strata.agentdocs.exceptions import SkillInstallError
from strata.agentdocs.main.update import update_skills
from strata.agentdocs.models import SkillUpdateResult
from strata.config.exceptions import ConfigError
from strata.config.models import Config
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import DiscoveredTree
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.models import EvaluationResult
from strata.reporting.classes.cli_style import CliStyle
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.catalog.main.build_ruleset import build_ruleset
from strata.scaffolding.constants import FAMILY_LABELS
from strata.scaffolding.helpers.output import prompt_yes_no
from strata.scaffolding.models import DriftSummary


def measure_drift(*, repository: Path, config: Config) -> DriftSummary:
    """Evaluate once without cache and aggregate selected family and path counts."""

    tree: DiscoveredTree = discover_files(config=config, repo_root=repository)
    rules: tuple[RuleSpec, ...] = build_ruleset(config=config, repo_root=repository)
    result: EvaluationResult = evaluate(tree=tree, ruleset=rules, config=config)
    selected_codes: frozenset[str] = frozenset(rule.code[:3] for rule in rules)
    rows: list[tuple[str, str, int]] = []
    for code, name in FAMILY_LABELS:
        if code in selected_codes:
            count: int = sum(fault.code.startswith(code) for fault in result.faults)
            rows.append((code, name, count))
    paths: set[Path] = {fault.path.resolve() for fault in result.faults}
    faults: tuple[Fault, ...] = result.faults
    return DriftSummary(family_counts=tuple(rows), fault_count=len(faults), file_count=len(paths))


def update_init_skills(
    *,
    repository: Path,
    config: Config,
    requested: bool | None,
    assume_yes: bool,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    style: CliStyle,
    home_dir: Path | None,
) -> None:
    """Prompt if needed, then install defaults while preserving config on failure."""

    install: bool = requested if requested is not None else assume_yes
    stdout.write("\n")
    if requested is None and not assume_yes:
        stdout.write(f"{style.header_marker()} {style.header_text('Install agent skill files?')}")
        install = prompt_yes_no(stdin=stdin, stdout=stdout, style=style, prompt="", default=True)
    else:
        resolved: str = "yes" if install else "no"
        stdout.write(
            f"{style.header_marker()} {style.header_text('Agent skill files')} "
            f"{style.provenance(f'- {resolved}')}\n"
        )
    if not install:
        stdout.write("\n    Run strata skills update when you are ready.\n")
        return
    try:
        rules: tuple[RuleSpec, ...] = build_ruleset(config=config, repo_root=repository)
        result: SkillUpdateResult = update_skills(
            config=config,
            rules=rules,
            project_dir=repository,
            home_dir=home_dir,
        )
    except (ConfigError, SkillInstallError, OSError) as error:
        stderr.write(f"Could not update agent skill files: {error}\n")
        return
    stdout.write("\n")
    for path in result.written_paths:
        relative: Path = path.relative_to(repository)
        stdout.write(f"    Updated {style.path(relative.as_posix())}\n")
