"""Associate static evaluate_rule calls with resolved rule references."""

from __future__ import annotations

from collections.abc import Mapping

from strata.analysis.classes.rule_test_associator import RuleTestAssociator
from strata.analysis.models import EvaluateRuleCallFact, RuleTestAssociationFact
from strata.analysis.types import Analysis


def associate_rule_tests(
    *, calls: tuple[EvaluateRuleCallFact, ...], modules: Mapping[str, Analysis]
) -> tuple[RuleTestAssociationFact, ...]:
    """Resolve rule re-exports and deduplicate cases by test function and location."""

    return RuleTestAssociator(modules=modules).associate(calls=calls)
