"""The decorator authoring style: @rule wraps a check function into a RuleSpec."""

from __future__ import annotations

from collections.abc import Callable

from strata.rules.authoring._helpers.envelope import (
    infer_kind,
    resolve_envelope,
    validate_code_namespace,
)
from strata.rules.authoring.constants import _RULE_SPEC_ATTRIBUTE
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family, RuleCheck, RuleKind, Severity


def rule(
    *,
    code: str,
    family: Family | str,
    slug: str,
    message: str,
    remediation: str | None = None,
    severity: Severity = Severity.ERROR,
    enabled_by_default: bool = True,
) -> Callable[[RuleCheck], RuleCheck]:
    """Attach a compiled rule spec to the decorated function and return it unchanged."""

    def decorate(check: RuleCheck) -> RuleCheck:
        resolved_family: Family = resolve_envelope(
            code=code,
            slug=slug,
            message=message,
            family=family,
        )
        kind: RuleKind = infer_kind(code)
        validate_code_namespace(code=code, kind=kind)
        spec: RuleSpec = RuleSpec(
            code=code,
            family=resolved_family,
            slug=slug,
            message=message,
            check=check,
            remediation=remediation,
            severity=severity,
            kind=kind,
            enabled_by_default=enabled_by_default,
        )
        _ = setattr(check, _RULE_SPEC_ATTRIBUTE, spec)
        return check

    return decorate
