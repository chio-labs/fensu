"""Versioned one-shot metadata host for native custom-rule skill generation."""

from __future__ import annotations

import json
import sys
from importlib.metadata import version
from pathlib import Path

from fensu.cli._helpers.rule_metadata import rule_metadata_value
from fensu.cli.constants import SKILLS_METADATA_PROTOCOL_VERSION
from fensu.cli.exceptions import CliCommandError
from fensu.config.main.load_project_config import load_project_config
from fensu.config.main.load_target_project_config import load_target_project_config
from fensu.config.models import LoadedConfig
from fensu.rules.catalog.main.build_check_rule_selection import build_check_rule_selection
from fensu.rules.catalog.models import RuleSelection


def main() -> int:
    """Load custom declarations once and return immutable catalogue and tier metadata."""

    request: object = json.load(sys.stdin)
    if not isinstance(request, dict) or request.get("protocol") != SKILLS_METADATA_PROTOCOL_VERSION:
        raise CliCommandError("incompatible native skills metadata protocol")
    root_value: object = request.get("project_root")
    if not isinstance(root_value, str):
        raise CliCommandError("custom metadata request requires project_root")
    target_value: object = request.get("target")
    if target_value is not None and not isinstance(target_value, str):
        raise CliCommandError("custom metadata request target must be a string or null")
    loaded: LoadedConfig = (
        load_project_config(Path(root_value))
        if target_value is None
        else load_target_project_config(start=Path(root_value), target=target_value)
    )
    project_root: Path = loaded.source.path.parent.resolve()
    selection: RuleSelection = build_check_rule_selection(
        config=loaded.config,
        repo_root=project_root,
        include_warnings=True,
        catalogue=loaded.catalogue,
    )
    response: dict[str, object] = {
        "protocol": SKILLS_METADATA_PROTOCOL_VERSION,
        "package_version": version("fensu"),
        "catalogue": [
            rule_metadata_value(
                rule=rule,
                current=loaded.config.rule_options.get(rule.code, {}),
            )
            for rule in selection.catalogue
        ],
        "blocking": [rule.code for rule in selection.blocking],
        "warnings": [rule.code for rule in selection.warnings],
        "ignored": [rule.code for rule in selection.ignored],
    }
    json.dump(response, sys.stdout, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    sys.stdout.write("\n")
    return 0
