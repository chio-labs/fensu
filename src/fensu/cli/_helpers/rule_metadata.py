"""Serialize canonical rule metadata for native consumers."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from fensu.rules.authoring.constants import MISSING
from fensu.rules.authoring.models import RuleOption, RuleSpec
from fensu.rules.authoring.types import RuleOptionValue


def rule_metadata_value(
    *, rule: RuleSpec, current: Mapping[str, RuleOptionValue]
) -> dict[str, object]:
    """Return one deterministic transport value for a compiled rule."""

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
            _option_metadata_value(option=option, current=current)
            for option in sorted(rule.options, key=lambda item: item.name)
        ],
        "constraints": [
            {
                "name": constraint.name,
                "description": constraint.description,
                "values": constraint.values,
            }
            for constraint in sorted(rule.constraints, key=lambda item: item.name)
        ],
        "thresholds": [threshold.value for threshold in rule.thresholds],
        "contract_behaviors": rule.contract_behaviors,
        "configuration_inputs": rule.configuration_inputs,
        "limits": [
            {"name": limit.name, "description": limit.description, "value": limit.value}
            for limit in sorted(rule.limits, key=lambda item: item.name)
        ],
    }


def serialized_rule_catalogue(*, rules: Sequence[RuleSpec]) -> bytes:
    """Serialize rules exactly as the checked-in native catalogue asset."""

    values: list[dict[str, object]] = [rule_metadata_value(rule=rule, current={}) for rule in rules]
    content: str = json.dumps(
        values,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{content}\n".encode()


def _option_metadata_value(
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
