"""Own the exact rule-code and selector grammar."""

from __future__ import annotations

import re

_CORE_RULE_CODE: re.Pattern[str] = re.compile(r"SF[A-Z][0-9]{3}")
_CUSTOM_RULE_CODE: re.Pattern[str] = re.compile(r"X[A-Z]*[0-9]+")
_CORE_RULE_SELECTOR: re.Pattern[str] = re.compile(r"SF(?:[A-Z][0-9]{0,3})?")
_CUSTOM_RULE_SELECTOR: re.Pattern[str] = re.compile(r"X[A-Z]*(?:[0-9]+)?")


def rule_code_is_exact(value: object) -> bool:
    """Return whether a value is one exact core or custom rule code."""

    return isinstance(value, str) and (
        _CORE_RULE_CODE.fullmatch(value) is not None
        or _CUSTOM_RULE_CODE.fullmatch(value) is not None
    )


def rule_selector_is_valid(value: object) -> bool:
    """Return whether a value is a syntactically valid rule-code prefix."""

    return isinstance(value, str) and (
        _CORE_RULE_SELECTOR.fullmatch(value) is not None
        or _CUSTOM_RULE_SELECTOR.fullmatch(value) is not None
    )


def code_matches_selector(*, code: str, selector: str) -> bool:
    """Return whether valid code and selector spellings have a prefix match."""

    return (
        rule_code_is_exact(code) and rule_selector_is_valid(selector) and code.startswith(selector)
    )
