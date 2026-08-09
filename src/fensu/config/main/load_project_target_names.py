"""Load validated analyzer target names without building catalogues."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fensu.analysis.main.require_analyzer_backend import require_analyzer_backend
from fensu.config._helpers.discovery import locate_config
from fensu.config._helpers.parse import parse_config_source
from fensu.config._helpers.validate import select_config_target, selected_config_target_names
from fensu.config.models import ConfigSource


def load_project_target_names(*, start: Path | None, target: str | None) -> tuple[str | None, ...]:
    """Return selected target names in deterministic order."""

    source: ConfigSource = locate_config(start)
    raw: Mapping[str, object] = parse_config_source(source)
    names: tuple[str | None, ...] = selected_config_target_names(raw=raw, target=target)
    for name in names:
        _, _, analyzer, _ = select_config_target(raw=raw, target=name)
        _ = require_analyzer_backend(analyzer)
    return names
