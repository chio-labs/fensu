"""Load validated configuration with its authoritative source location."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fensu.config._helpers.discovery import locate_config
from fensu.config._helpers.parse import parse_config_source
from fensu.config._helpers.validate import validate_config
from fensu.config.main._build_config import build_config
from fensu.config.main.build_config_for_rules import build_config_for_rules
from fensu.config.models import Config, ConfigSource, LoadedConfig
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.catalog.main.build_catalogue import build_catalogue


def load_project_config(start: Path | None = None) -> LoadedConfig:
    """Load validated config together with its authoritative source location."""

    source: ConfigSource = locate_config(start)
    raw_config: Mapping[str, object] = parse_config_source(source)
    validate_config(raw_config)
    bootstrap_raw: dict[str, object] = dict(raw_config)
    _ = bootstrap_raw.pop("rule_options", None)
    bootstrap: Config = build_config(bootstrap_raw)
    catalogue: tuple[RuleSpec, ...] = build_catalogue(
        config=bootstrap,
        repo_root=source.path.parent.resolve(),
    )
    return LoadedConfig(
        config=build_config_for_rules(raw=raw_config, rules=catalogue),
        source=source,
        catalogue=catalogue,
    )
