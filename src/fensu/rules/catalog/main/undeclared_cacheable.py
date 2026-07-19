"""Report undeclared custom rules whose source passes the hermetic scan."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import RuleKind
from fensu.rules.catalog._helpers.hermeticity import rule_appears_cacheable


def undeclared_cacheable_codes(
    *,
    rules: tuple[RuleSpec, ...],
    allowed_packages: frozenset[str],
) -> tuple[str, ...]:
    """Return sorted codes of undeclared custom rules that appear cacheable."""

    codes: set[str] = set()
    for rule in rules:
        if rule.kind is not RuleKind.CUSTOM or rule.cacheable is not None:
            continue
        if rule.code in codes:
            continue
        if rule_appears_cacheable(rule=rule, allowed_packages=allowed_packages):
            codes.add(rule.code)
    return tuple(sorted(codes))
