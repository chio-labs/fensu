"""Prepare configured and discovered inputs for one check invocation."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from fensu.cli._helpers.check_paths import invocation_path
from fensu.cli.models import CheckInputs
from fensu.config.main.load_target_project_config import load_target_project_config
from fensu.config.main.resolve_target_root import resolve_target_root
from fensu.config.models import Config, LoadedConfig, ResolvedTargetRoot
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
        callback=lambda: load_target_project_config(start=invocation_dir, target=args.target),
    )
    project_dir: Path = loaded.source.path.parent.resolve()
    resolved_target: ResolvedTargetRoot = resolve_target_root(
        config=loaded.config, repo_root=project_dir
    )
    target_dir: Path = resolved_target.path
    config: Config = _configured(args=args, loaded=loaded, invocation_dir=invocation_dir)
    rule_selection: RuleSelection = OPERATION_COUNTERS.measure(
        operation=PHASE_CATALOGUE_NANOSECONDS,
        callback=lambda: build_check_rule_selection(
            config=loaded.config,
            repo_root=project_dir,
            project_root=target_dir,
            include_warnings=args.warn,
            catalogue=loaded.catalogue,
        ),
    )
    tree: DiscoveredTree = OPERATION_COUNTERS.measure(
        operation=PHASE_DISCOVERY_NANOSECONDS,
        callback=lambda: discover_files(config=config, repo_root=project_dir),
    )
    validate_rule_exceptions(config=config, repo_root=target_dir)
    return CheckInputs(
        loaded=loaded,
        project_dir=project_dir,
        rule_selection=rule_selection,
        config=config,
        tree=tree,
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
