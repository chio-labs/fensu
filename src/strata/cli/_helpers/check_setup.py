"""Prepare configured and discovered inputs for one check invocation."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from strata.cli._helpers.check_paths import invocation_path
from strata.cli.models import CheckInputs
from strata.config.main.load_project_config import load_project_config
from strata.config.models import Config, LoadedConfig
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import DiscoveredTree
from strata.evaluation.main.validate_rule_exceptions import validate_rule_exceptions
from strata.instrumentation.constants import (
    OPERATION_COUNTERS,
    PHASE_CATALOGUE_NANOSECONDS,
    PHASE_CONFIG_NANOSECONDS,
    PHASE_DISCOVERY_NANOSECONDS,
)
from strata.rules.catalog.main.build_check_rule_selection import build_check_rule_selection
from strata.rules.catalog.models import RuleSelection


def prepare_check_inputs(*, args: argparse.Namespace, invocation_dir: Path) -> CheckInputs:
    """Load configuration, rules, discovery, and validation for one check."""

    loaded: LoadedConfig = OPERATION_COUNTERS.measure(
        operation=PHASE_CONFIG_NANOSECONDS,
        callback=lambda: load_project_config(invocation_dir),
    )
    project_dir: Path = loaded.source.path.parent.resolve()
    rule_selection: RuleSelection = OPERATION_COUNTERS.measure(
        operation=PHASE_CATALOGUE_NANOSECONDS,
        callback=lambda: build_check_rule_selection(
            config=loaded.config,
            repo_root=project_dir,
            include_warnings=args.warn,
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
