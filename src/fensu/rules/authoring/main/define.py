"""The decorator authoring style: @rule wraps a check function into a RuleSpec."""

from __future__ import annotations

from collections.abc import Callable

from fensu.rules.authoring._helpers.envelope import (
    infer_kind,
    resolve_envelope,
    validate_code_namespace,
)
from fensu.rules.authoring._helpers.subjects import infer_rule_subject
from fensu.rules.authoring.constants import _RULE_SPEC_ATTRIBUTE
from fensu.rules.authoring.exceptions import RuleDefinitionError
from fensu.rules.authoring.models import RuleOption, RuleSpec
from fensu.rules.authoring.types import (
    ExecutionOwner,
    Family,
    RuleCheck,
    RuleKind,
    RuleSubjectKind,
    Severity,
)


def rule(
    *,
    code: str,
    family: Family | str,
    slug: str,
    message: str,
    remediation: str | None = None,
    severity: Severity = Severity.ERROR,
    enabled_by_default: bool = True,
    cacheable: bool | None = None,
    execution_owner: ExecutionOwner | None = None,
    options: tuple[RuleOption[object], ...] = (),
) -> Callable[[RuleCheck], RuleCheck]:
    """Attach a compiled rule spec to the decorated function and return it unchanged."""

    def decorate(check: RuleCheck) -> RuleCheck:
        if any(not isinstance(option, RuleOption) for option in options):
            raise RuleDefinitionError(f"rule {code} options must contain only RuleOption values")
        option_names: tuple[str, ...] = tuple(option.name for option in options)
        if len(set(option_names)) != len(option_names):
            raise RuleDefinitionError(f"rule {code} declares duplicate option names")
        resolved_family: Family = resolve_envelope(
            code=code,
            slug=slug,
            message=message,
            family=family,
        )
        kind: RuleKind = infer_kind(code)
        validate_code_namespace(code=code, kind=kind)
        subject_kind, subject_parameter, context_parameter = infer_rule_subject(check=check)
        inferred_owner: ExecutionOwner = (
            ExecutionOwner.PROJECT
            if subject_kind is RuleSubjectKind.PROJECT
            else ExecutionOwner.FILE
        )
        if (
            subject_kind is not RuleSubjectKind.LEGACY
            and execution_owner is not None
            and execution_owner is not inferred_owner
        ):
            raise RuleDefinitionError(
                f"{subject_kind.value} rule signature conflicts with explicit execution_owner "
                f"{execution_owner.value!r}"
            )
        resolved_execution_owner: ExecutionOwner = execution_owner or inferred_owner
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
            cacheable=cacheable,
            execution_owner=resolved_execution_owner,
            subject_kind=subject_kind,
            subject_parameter=subject_parameter,
            context_parameter=context_parameter,
            options=tuple(options),
        )
        _ = setattr(check, _RULE_SPEC_ATTRIBUTE, spec)
        return check

    return decorate
