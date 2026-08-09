"""Load validated configuration with its authoritative source location."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

from fensu.analysis.main.require_analyzer_backend import require_analyzer_backend
from fensu.config._helpers.discovery import locate_config
from fensu.config._helpers.parse import parse_config_source
from fensu.config._helpers.validate import select_config_target, validate_config
from fensu.config.main._build_config import build_config
from fensu.config.main.build_config_for_rules import build_config_for_rules
from fensu.config.main.resolve_target_root import resolve_target_root
from fensu.config.models import Config, ConfigSource, LoadedConfig, ResolvedTargetRoot
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.catalog.main.build_catalogue import build_catalogue


def load_project_config(start: Path | None = None) -> LoadedConfig:
    """Load validated config together with its authoritative source location."""

    return _load_project_config(start=start, target=None)


def _load_project_config(*, start: Path | None, target: str | None) -> LoadedConfig:
    """Load validated config for an optional named target."""

    source: ConfigSource = locate_config(start)
    parsed: Mapping[str, object] = parse_config_source(source)
    raw_config, target_name, analyzer, target_root = select_config_target(raw=parsed, target=target)
    validate_config(raw_config)
    bootstrap_raw: dict[str, object] = dict(raw_config)
    _ = bootstrap_raw.pop("rule_options", None)
    bootstrap: Config = replace(
        build_config(bootstrap_raw),
        analyzer=analyzer,
        target=target_name,
        target_root=target_root,
    )
    _ = require_analyzer_backend(bootstrap.analyzer)
    repository_root: Path = source.path.parent.resolve()
    resolved_target: ResolvedTargetRoot = resolve_target_root(
        config=bootstrap, repo_root=repository_root
    )
    bootstrap = replace(bootstrap, target_root=resolved_target.repository_relative)
    catalogue: tuple[RuleSpec, ...] = build_catalogue(
        config=bootstrap,
        repo_root=resolved_target.path,
    )
    config: Config = replace(
        build_config_for_rules(raw=raw_config, rules=catalogue),
        analyzer=analyzer,
        target=target_name,
        target_root=resolved_target.repository_relative,
    )
    return LoadedConfig(
        config=config,
        source=source,
        catalogue=catalogue,
    )
