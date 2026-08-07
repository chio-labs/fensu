"""Build custom exemplar decorators from canonical core metadata."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace

from fensu import ExecutionOwner, Family, rule
from fensu.rules.authoring.constants import _RULE_SPEC_ATTRIBUTE
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import RuleCheck
from fensu.rules.catalog.main._get_rule_spec import get_rule_spec


def equivalent_rule(
    *,
    core_code: str,
    code: str,
    slug: str,
    execution_owner: ExecutionOwner | None = None,
) -> Callable[[RuleCheck], RuleCheck]:
    """Return a custom-rule decorator carrying canonical core prose."""

    core: RuleSpec = get_rule_spec(code=core_code)
    base: Callable[[RuleCheck], RuleCheck] = rule(
        code=code,
        family=Family.CUSTOM,
        slug=slug,
        message=core.message,
        remediation=core.remediation,
        execution_owner=core.execution_owner if execution_owner is None else execution_owner,
    )

    def decorate(check: RuleCheck) -> RuleCheck:
        decorated: RuleCheck = base(check)
        canonical: RuleSpec = canonical_equivalent_rule(core_code=core_code, check=decorated)
        _ = setattr(decorated, _RULE_SPEC_ATTRIBUTE, canonical)
        return decorated

    return decorate


def canonical_equivalent_rule(*, core_code: str, check: RuleCheck) -> RuleSpec:
    """Replace one exemplar's policy metadata with its canonical core contract."""

    core: RuleSpec = get_rule_spec(code=core_code)
    spec: RuleSpec = getattr(check, _RULE_SPEC_ATTRIBUTE)
    return replace(
        spec,
        message=core.message,
        remediation=core.remediation,
        severity=core.severity,
        enabled_by_default=core.enabled_by_default,
        cacheable=core.cacheable,
        execution_owner=core.execution_owner,
        constraints=core.constraints,
        thresholds=core.thresholds,
        contract_behaviors=core.contract_behaviors,
        configuration_inputs=core.configuration_inputs,
        limits=core.limits,
    )


def canonical_equivalent_rules(rules: Mapping[str, RuleCheck]) -> dict[str, RuleCheck]:
    """Attach canonical metadata to every core-to-exemplar registry entry."""

    canonical: dict[str, RuleCheck] = {}
    for core_code, check in rules.items():
        _ = setattr(
            check,
            _RULE_SPEC_ATTRIBUTE,
            canonical_equivalent_rule(core_code=core_code, check=check),
        )
        canonical[core_code] = check
    return canonical
