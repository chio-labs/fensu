"""Prepare configured and discovered inputs for one check invocation."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from fensu.cli._helpers.check_paths import invocation_path
from fensu.cli.exceptions import CliCommandError
from fensu.cli.models import CheckInputs
from fensu.config.main.load_project_config import load_project_config
from fensu.config.models import Config, LoadedConfig
from fensu.discovery.main.discover_files import discover_files
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation.main.validate_rule_exceptions import validate_rule_exceptions
from fensu.instrumentation.constants import (
    OPERATION_COUNTERS,
    PHASE_CATALOGUE_NANOSECONDS,
    PHASE_CONFIG_NANOSECONDS,
    PHASE_DISCOVERY_NANOSECONDS,
)
from fensu.rules.catalog.main.build_check_rule_selection import build_check_rule_selection
from fensu.rules.catalog.models import RuleSelection


def prepare_check_inputs(*, args: argparse.Namespace, invocation_dir: Path) -> CheckInputs:
    """Load configuration, rules, discovery, and validation for one check."""

    loaded: LoadedConfig = OPERATION_COUNTERS.measure(
        operation=PHASE_CONFIG_NANOSECONDS,
        callback=lambda: load_project_config(invocation_dir),
    )
    project_dir: Path = loaded.source.path.parent.resolve()
    memory_result: object | None = _memory_result(loaded=loaded, project_dir=project_dir)
    rule_selection: RuleSelection = OPERATION_COUNTERS.measure(
        operation=PHASE_CATALOGUE_NANOSECONDS,
        callback=lambda: build_check_rule_selection(
            config=loaded.config,
            repo_root=project_dir,
            include_warnings=args.warn,
            catalogue=loaded.catalogue,
        ),
    )
    config: Config = _configured(args=args, loaded=loaded, invocation_dir=invocation_dir)
    tree: DiscoveredTree = OPERATION_COUNTERS.measure(
        operation=PHASE_DISCOVERY_NANOSECONDS,
        callback=lambda: discover_files(config=config, repo_root=project_dir),
    )
    validate_rule_exceptions(config=config, repo_root=tree.repo_root.path)
    return CheckInputs(
        loaded=loaded,
        project_dir=project_dir,
        rule_selection=rule_selection,
        config=config,
        tree=tree,
        memory_result=memory_result,
    )


def _configured(
    *,
    args: argparse.Namespace,
    loaded: LoadedConfig,
    invocation_dir: Path,
) -> Config:
    config: Config = loaded.config
    if args.paths:
        config = replace(
            config,
            roots=tuple(
                invocation_path(value=value, invocation_dir=invocation_dir) for value in args.paths
            ),
        )
    if args.cache_enabled is not None:
        config = replace(
            config,
            cache=replace(config.cache, enabled=args.cache_enabled),
        )
    return config


def _memory_result(*, loaded: LoadedConfig, project_dir: Path) -> object | None:
    if not loaded.config.experimental.memory:
        return None
    from fensu.memory.constants import MEMORY_DATABASE_DIRECTORY, MEMORY_DATABASE_FILENAME
    from fensu.memory.exceptions import MemoryError
    from fensu.memory.main.check_memory import check_memory
    from fensu.memory.models import MemoryProject

    project: MemoryProject = MemoryProject(
        repository_root=project_dir,
        database_path=project_dir / MEMORY_DATABASE_DIRECTORY / MEMORY_DATABASE_FILENAME,
    )
    try:
        return check_memory(project)
    except MemoryError as error:
        raise CliCommandError(str(error)) from error
