"""Initialize Strata configuration for a detected repository layout."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TextIO

from strata.config.exceptions import ConfigError
from strata.evaluation.exceptions import ParseError
from strata.reporting.classes.cli_style import CliStyle
from strata.scaffolding._helpers.drift import measure_drift, update_init_skills
from strata.scaffolding._helpers.execution import execute_init_plan
from strata.scaffolding._helpers.output import (
    write_classification,
    write_drift,
    write_empty_success,
    write_next,
)
from strata.scaffolding._helpers.planning import (
    build_init_plan,
    count_runtime_python_files,
    interaction_decision,
    preflight_existing_config,
    validate_option_applicability,
)
from strata.scaffolding.exceptions import InitError, ScaffoldingError
from strata.scaffolding.main.detect_repository_layout import detect_repository_layout
from strata.scaffolding.models import (
    DetectedRepositoryLayout,
    DriftSummary,
    InitExecution,
    InitOptions,
    InitPlan,
)
from strata.scaffolding.types import InteractionDecision


def run_init(
    *,
    repository: Path,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    options: InitOptions,
    use_color: bool,
    home_dir: Path | None = None,
) -> int:
    """Detect, confirm, validate, write, evaluate, and optionally install skills."""

    try:
        resolved: Path = repository.resolve()
        existing_config: Path | None = preflight_existing_config(repository=resolved)
        if existing_config is not None:
            stdout.write(
                f"Strata configuration already exists: {existing_config} (nothing to do)\n"
            )
            return 0
        detected: DetectedRepositoryLayout = detect_repository_layout(repository=resolved)
        validate_option_applicability(options=options, detected=detected)
        decision: InteractionDecision = interaction_decision(options=options, detected=detected)
        _require_tty(decision=decision, stdin=stdin, stdout=stdout)
        style: CliStyle = CliStyle(use_color=use_color)
        plan: InitPlan = build_init_plan(
            repository=resolved,
            detected=detected,
            options=options,
            stdin=stdin,
            stdout=stdout,
            style=style,
        )
        runtime_count: int = count_runtime_python_files(repository=resolved, roots=plan.roots)
        config, execution = execute_init_plan(repository=resolved, plan=plan)
    except (
        ScaffoldingError,
        ConfigError,
        ParseError,
        tomllib.TOMLDecodeError,
        OSError,
        UnicodeError,
    ) as error:
        stderr.write(f"{error}\n")
        return 2
    _write_success(
        plan=plan,
        execution=execution,
        runtime_count=runtime_count,
        stdout=stdout,
        style=style,
    )
    try:
        summary: DriftSummary = measure_drift(repository=resolved, config=config)
    except (ConfigError, ParseError, OSError, UnicodeError) as error:
        stderr.write(f"Warning: could not measure current drift: {error}\n")
    else:
        write_drift(stdout=stdout, style=style, summary=summary)
    try:
        update_init_skills(
            repository=resolved,
            config=config,
            requested=options.skills,
            assume_yes=options.yes,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            style=style,
            home_dir=home_dir,
        )
    except InitError as error:
        stderr.write(f"{error}\n")
        return 2
    write_next(stdout=stdout, style=style)
    return 0


def _require_tty(*, decision: InteractionDecision, stdin: TextIO, stdout: TextIO) -> None:
    if decision is InteractionDecision.TTY_REQUIRED and not (stdin.isatty() and stdout.isatty()):
        raise InitError("Interactive initialization requires a TTY; use --yes or explicit options.")


def _write_success(
    *,
    plan: InitPlan,
    execution: InitExecution,
    runtime_count: int,
    stdout: TextIO,
    style: CliStyle,
) -> None:
    if plan.project_name is not None:
        write_empty_success(
            stdout=stdout,
            style=style,
            created_paths=execution.created_paths,
        )
        return
    write_classification(stdout=stdout, style=style, plan=plan, python_file_count=runtime_count)
