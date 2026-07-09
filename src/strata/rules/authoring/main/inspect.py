"""Inspect loaded modules for decorator-authored rule metadata."""

from __future__ import annotations

from types import ModuleType

from strata.rules.authoring.constants import _RULE_SPEC_ATTRIBUTE
from strata.rules.authoring.models import RuleSpec


def rule_specs_in_module(*, module: ModuleType) -> tuple[RuleSpec, ...]:
    """Return rule specs attached to functions defined by the given module."""

    rules: list[RuleSpec] = []
    seen_codes: set[str] = set()
    for value in vars(module).values():
        if getattr(value, "__module__", None) != module.__name__:
            continue
        spec: object = getattr(value, _RULE_SPEC_ATTRIBUTE, None)
        if isinstance(spec, RuleSpec) and spec.code not in seen_codes:
            rules.append(spec)
            seen_codes.add(spec.code)
    return tuple(rules)
