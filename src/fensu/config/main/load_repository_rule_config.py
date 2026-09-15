"""Load one repository-owned custom-rule policy independently of analyzer targets."""

from pathlib import Path

from fensu.config._helpers.discovery import locate_config
from fensu.config._helpers.parse import parse_config_source
from fensu.config._helpers.repository_rules import build_repository_rule_config
from fensu.config.models import ConfigSource, LoadedConfig


def load_repository_rule_config(*, start: Path | None) -> LoadedConfig | None:
    """Return validated repository-rule configuration, or None when absent."""

    source: ConfigSource = locate_config(start)
    return build_repository_rule_config(source=source, parsed=parse_config_source(source))
