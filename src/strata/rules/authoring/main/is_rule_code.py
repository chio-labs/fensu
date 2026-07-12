"""Expose exact rule-code grammar through the authoring boundary."""

from __future__ import annotations

from strata.rules.authoring.helpers.code_grammar import rule_code_is_exact


def is_rule_code(value: object) -> bool:
    """Return whether a value is one exact core or custom rule code."""

    return rule_code_is_exact(value)
