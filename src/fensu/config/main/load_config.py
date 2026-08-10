"""Load a validated fensu Config from the nearest supported config source."""

from __future__ import annotations

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
from fensu.config.main.build_config import build_config
from fensu.config.main.load_project_config import load_project_config
from fensu.config.main.resolve_target_root import resolve_target_root
from fensu.config.models import Config, ConfigSource, ResolvedTargetRoot
from fensu.config.types import AnalyzerId


def load_config(start: Path | None = None) -> Config:
    """Load and validate fensu config starting from a path or the current directory."""

    source: ConfigSource = locate_config(start)
    parsed: dict[str, object] = dict(parse_config_source(source))
    raw, target_name, analyzer, target_root = select_config_target(raw=parsed, target=None)
    validate_config(raw=raw, analyzer=analyzer)
    if raw.get("rule_options"):
        return load_project_config(start).config
    base_config: Config = build_config(raw)
    config: Config = replace(
        base_config,
        analyzer=analyzer,
        target=target_name,
        target_root=target_root,
        framework=base_config.framework
        or (DEFAULT_WEB_FRAMEWORK if analyzer is AnalyzerId.SVELTE else None),
        shadcn=base_config.shadcn,
        select=DEFAULT_WEB_SELECT
        if analyzer != PYTHON_ANALYZER and SELECT_CONFIG_KEY not in raw
        else base_config.select,
    )
    _ = require_analyzer_backend(config.analyzer)
    resolved_target: ResolvedTargetRoot = resolve_target_root(
        config=config, repo_root=source.path.parent
    )
    return replace(config, target_root=resolved_target.repository_relative)
