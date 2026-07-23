"""Versioned one-shot metadata host for native custom-rule skill generation."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from importlib.metadata import version
from pathlib import Path

from fensu.cli.constants import SKILLS_METADATA_PROTOCOL_VERSION
from fensu.cli.exceptions import CliCommandError
from fensu.config.main.load_project_config import load_project_config
from fensu.config.models import LoadedConfig
from fensu.rules.authoring.constants import MISSING
from fensu.rules.authoring.models import RuleOption, RuleSpec
from fensu.rules.authoring.types import RuleOptionValue
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
    loaded: LoadedConfig = load_project_config(Path(root_value))
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
            _rule_value(
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


def _rule_value(*, rule: RuleSpec, current: Mapping[str, RuleOptionValue]) -> dict[str, object]:
    return {
        "code": rule.code,
        "family": rule.family.value,
        "slug": rule.slug,
        "message": rule.message,
        "remediation": rule.remediation,
        "severity": rule.severity.value,
        "enabled_by_default": rule.enabled_by_default,
        "execution_owner": rule.execution_owner.value,
        "kind": rule.kind.value,
        "source": rule.source,
        "cacheable": bool(rule.cacheable),
        "options": [
            _option_value(option=option, current=current)
            for option in sorted(rule.options, key=lambda item: item.name)
        ],
    }


def _option_value(
    *, option: RuleOption[object], current: Mapping[str, RuleOptionValue]
) -> dict[str, object]:
    return {
        "name": option.name,
        "kind": option.kind.value,
        "required": option.required,
        "default": None if option.default is MISSING else option.default,
        "current_value": current[option.name],
        "description": option.description,
        "choices": option.choices,
        "minimum": option.minimum,
        "maximum": option.maximum,
        "minimum_items": option.minimum_items,
    }
