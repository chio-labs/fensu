"""Resolve one custom-rule harness input to its compiled rule specification."""

from __future__ import annotations

from types import FunctionType

from fensu.rules.authoring.constants import _RULE_SPEC_ATTRIBUTE
from fensu.rules.authoring.exceptions import RuleDefinitionError
from fensu.rules.authoring.models import RuleSpec


def resolve_rule_spec(*, value: object) -> RuleSpec:
    """Resolve one internal spec or a function decorated by Fensu's public rule API."""

    if isinstance(value, RuleSpec):
        return value
    if not isinstance(value, FunctionType):
        raise RuleDefinitionError("rule must be a RuleSpec or a function decorated with @rule.")
    spec: object = value.__dict__.get(_RULE_SPEC_ATTRIBUTE)
    if not isinstance(spec, RuleSpec) or spec.check is not value:
        raise RuleDefinitionError("rule function must be decorated with Fensu's @rule decorator.")
    return spec
