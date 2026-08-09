"""Load validated analyzer target names without building catalogues."""

from __future__ import annotations

from pathlib import Path

from fensu.config._helpers.discovery import locate_config
from fensu.config._helpers.parse import parse_config_source
from fensu.config._helpers.validate import selected_config_target_names
from fensu.config.models import ConfigSource


def load_project_target_names(*, start: Path | None, target: str | None) -> tuple[str | None, ...]:
    """Return selected target names in deterministic order."""

    source: ConfigSource = locate_config(start)
    return selected_config_target_names(raw=parse_config_source(source), target=target)
