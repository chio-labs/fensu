"""Load validated configuration with its authoritative source location."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

from fensu.analysis.main.require_analyzer_backend import require_analyzer_backend
from fensu.config._helpers.discovery import locate_config
from fensu.config._helpers.parse import parse_config_source
from fensu.config._helpers.validate import select_config_target, validate_config
from fensu.config.constants import (
    DEFAULT_WEB_FRAMEWORK,
    DEFAULT_WEB_SELECT,
    PYTHON_ANALYZER,
    SELECT_CONFIG_KEY,
)
from fensu.config.exceptions import ConfigError
from fensu.config.main._build_config import build_config
from fensu.config.main.build_config_for_rules import build_config_for_rules
from fensu.config.main.resolve_target_root import resolve_target_root
from fensu.config.models import Config, ConfigSource, LoadedConfig, ResolvedTargetRoot
from fensu.config.types import AnalyzerId
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
    validate_config(raw=raw_config, analyzer=analyzer)
    bootstrap_raw: dict[str, object] = dict(raw_config)
    _ = bootstrap_raw.pop("rule_options", None)
    base_bootstrap: Config = build_config(raw=bootstrap_raw, analyzer=analyzer)
    bootstrap: Config = replace(
        base_bootstrap,
        analyzer=analyzer,
        target=target_name,
        target_root=target_root,
        framework=base_bootstrap.framework
        or (DEFAULT_WEB_FRAMEWORK if analyzer is AnalyzerId.SVELTE else None),
        shadcn=base_bootstrap.shadcn,
        select=DEFAULT_WEB_SELECT
        if analyzer != PYTHON_ANALYZER and SELECT_CONFIG_KEY not in raw_config
        else base_bootstrap.select,
    )
    _ = require_analyzer_backend(bootstrap.analyzer)
    if bootstrap.analyzer != PYTHON_ANALYZER and (
        bootstrap.rule_paths or bootstrap.rule_modules or bool(raw_config.get("rule_options"))
    ):
        raise ConfigError(
            f"Native {bootstrap.analyzer.value} targets do not support Python-hosted custom rules."
        )
    repository_root: Path = source.path.parent.resolve()
    resolved_target: ResolvedTargetRoot = resolve_target_root(
        config=bootstrap, repo_root=repository_root
    )
    _validate_web_dependencies(config=bootstrap, project_root=resolved_target.path)
    bootstrap = replace(bootstrap, target_root=resolved_target.repository_relative)
    catalogue: tuple[RuleSpec, ...] = build_catalogue(
        config=bootstrap,
        repo_root=resolved_target.path,
    )
    base_config: Config = build_config_for_rules(raw=raw_config, rules=catalogue, analyzer=analyzer)
    config: Config = replace(
        base_config,
        analyzer=analyzer,
        target=target_name,
        target_root=resolved_target.repository_relative,
        framework=base_config.framework
        or (DEFAULT_WEB_FRAMEWORK if analyzer is AnalyzerId.SVELTE else None),
        shadcn=base_config.shadcn,
        select=DEFAULT_WEB_SELECT
        if analyzer != PYTHON_ANALYZER and SELECT_CONFIG_KEY not in raw_config
        else base_config.select,
    )
    return LoadedConfig(
        config=config,
        source=source,
        catalogue=catalogue,
    )


def _validate_web_dependencies(*, config: Config, project_root: Path) -> None:
    canonical_root: Path = project_root.resolve()
    for configured in (config.shadcn, config.openapi):
        if configured is None:
            continue
        path: Path = project_root / configured
        if not path.is_file():
            raise ConfigError(
                f"Configured target-local web dependency does not exist: {configured}."
            )
        if not path.resolve().is_relative_to(canonical_root):
            raise ConfigError(
                f"Configured target-local web dependency escapes the target: {configured}."
            )
    if config.ui_kit is not None:
        ui_kit: Path = project_root / config.ui_kit
        if ui_kit.exists() and not ui_kit.resolve().is_relative_to(canonical_root):
            raise ConfigError(
                f"Configured target-local UI-kit path escapes the target: {config.ui_kit}."
            )
