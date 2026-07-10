"""Helpers for repository-aware skill guidance tests."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.constants import CORE_RULES


def core_rules_for_codes(rule_codes: tuple[str, ...]) -> tuple[RuleSpec, ...]:
    """Return core rules in the requested order."""

    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in CORE_RULES}
    return tuple(rules_by_code[code] for code in rule_codes)


def core_rule_codes_for_prefix(prefix: str) -> tuple[str, ...]:
    """Return core rule codes that share a family prefix."""

    return tuple(rule.code for rule in CORE_RULES if rule.code.startswith(prefix))


def structure_fragment_is_absent(*, document: str, fragment: str) -> bool:
    """Return whether a structural claim is absent from its generated scope."""

    guidance: str = document.partition("## Active Rules")[0]
    if fragment.startswith("## "):
        return fragment not in guidance
    structure: str = guidance.partition("## Repository Structure")[2]
    return fragment not in structure
