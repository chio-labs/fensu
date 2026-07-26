"""Build custom exemplar decorators from canonical core metadata."""

from __future__ import annotations

from collections.abc import Callable
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
    execution_owner: ExecutionOwner = ExecutionOwner.FILE,
) -> Callable[[RuleCheck], RuleCheck]:
    """Return a custom-rule decorator carrying canonical core prose."""

    core: RuleSpec = get_rule_spec(code=core_code)
    base: Callable[[RuleCheck], RuleCheck] = rule(
        code=code,
        family=Family.CUSTOM,
        slug=slug,
        message=core.message,
        remediation=core.remediation,
        execution_owner=execution_owner,
    )

    def decorate(check: RuleCheck) -> RuleCheck:
        decorated: RuleCheck = base(check)
        spec: RuleSpec = getattr(decorated, _RULE_SPEC_ATTRIBUTE)
        canonical: RuleSpec = replace(
            spec,
            constraints=core.constraints,
            thresholds=core.thresholds,
            contract_behaviors=core.contract_behaviors,
            configuration_inputs=core.configuration_inputs,
            limits=core.limits,
        )
        _ = setattr(decorated, _RULE_SPEC_ATTRIBUTE, canonical)
        return decorated

    return decorate
