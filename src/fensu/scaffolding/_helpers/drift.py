"""Uncached evaluation and summarized starting-ruleset drift."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TextIO

from fensu.agentdocs.exceptions import SkillInstallError
from fensu.agentdocs.main.build_generation_context import build_generation_context
from fensu.agentdocs.main.update import update_skills
from fensu.agentdocs.models import SkillGenerationContext, SkillUpdateResult
from fensu.cache.fingerprints.main.build_global import build_global_fingerprint
from fensu.cache.fingerprints.models import CacheFingerprint, GlobalFingerprintBuild
from fensu.cache.results.main.evaluate import evaluate_with_cache
from fensu.cache.results.models import CacheEvaluation
from fensu.config.exceptions import ConfigError
from fensu.config.models import Config, ConfigSource
from fensu.config.types import ConfigSourceKind
from fensu.discovery.main.discover_files import discover_files
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation.main.evaluate import evaluate
from fensu.evaluation.main.resolve_worker_count import resolve_worker_count
from fensu.evaluation.models import EvaluationResult
from fensu.reporting.classes.cli_style import CliStyle
from fensu.rules.authoring.models import Fault, RuleSpec
from fensu.rules.catalog.main.build_check_rule_selection import build_check_rule_selection
from fensu.rules.catalog.main.build_ruleset import build_ruleset
from fensu.rules.catalog.models import RuleSelection
from fensu.scaffolding._helpers.output import prompt_yes_no
from fensu.scaffolding.constants import CONFIG_FILE_NAME, FAMILY_LABELS
from fensu.scaffolding.exceptions import InitError
from fensu.scaffolding.models import DriftSummary


def measure_drift(*, repository: Path, config: Config) -> DriftSummary:
    """Evaluate once without cache and aggregate selected family and path counts."""

    tree: DiscoveredTree = discover_files(config=config, repo_root=repository)
    rules: tuple[RuleSpec, ...] = build_ruleset(config=config, repo_root=repository)
    fingerprint_build: GlobalFingerprintBuild = build_global_fingerprint(
        config=config,
        ruleset=rules,
        repo_root=repository,
    )
    fingerprint: CacheFingerprint | None = fingerprint_build.fingerprint
    if fingerprint is None:
        result: EvaluationResult = evaluate(tree=tree, ruleset=rules, config=config)
    else:
        cached: CacheEvaluation = evaluate_with_cache(
            tree=tree,
            ruleset=rules,
            config=config,
            global_fingerprint=fingerprint,
            allow_short_circuit=False,
            jobs=resolve_worker_count(target_count=len(tree.files)),
        )
        if cached.result is None:
            raise InitError("Cache-aware drift evaluation returned no logical result.")
        result = cached.result
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
        stdout.write("\n    Run fensu skills when you are ready.\n")
        return
    try:
        selection: RuleSelection = build_check_rule_selection(
            config=config, repo_root=repository, include_warnings=True
        )
        context: SkillGenerationContext = build_generation_context(
            config=config,
            source=ConfigSource(
                path=repository / CONFIG_FILE_NAME,
                kind=ConfigSourceKind.FENSU_TOML,
            ),
            project_root=repository,
            selection=selection,
        )
        result: SkillUpdateResult = update_skills(
            context=context,
            home_dir=home_dir,
        )
    except (ConfigError, SkillInstallError, OSError) as error:
        stderr.write(f"Could not update agent skill files: {error}\n")
        return
    stdout.write("\n")
    for path in result.written_paths:
        relative: str = Path(os.path.relpath(path, repository)).as_posix()
        stdout.write(f"    Updated {style.path(relative)}\n")
