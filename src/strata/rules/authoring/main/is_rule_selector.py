"""Expose rule-selector grammar through the authoring boundary."""

from __future__ import annotations

from strata.rules.authoring.helpers.code_grammar import rule_selector_is_valid


def is_rule_selector(value: object) -> bool:
    """Return whether a value is a syntactically valid rule-code prefix."""

    return rule_selector_is_valid(value)
