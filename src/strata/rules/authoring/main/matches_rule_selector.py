"""Expose rule code-to-selector matching through the authoring boundary."""

from __future__ import annotations

from strata.rules.authoring._helpers.code_grammar import code_matches_selector


def matches_rule_selector(*, code: str, selector: str) -> bool:
    """Return whether a valid code starts with a valid selector."""

    return code_matches_selector(code=code, selector=selector)
