"""Tests for the unified exact rule-code and selector grammar."""

from __future__ import annotations

import pytest

from fensu.rules.authoring.main.is_rule_code import is_rule_code
from fensu.rules.authoring.main.is_rule_selector import is_rule_selector
from fensu.rules.authoring.main.matches_rule_selector import matches_rule_selector
from tests.unit.src.fensu.rules.authoring._test_types import (
    RuleGrammarTestCase,
    RuleSelectorMatchTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        RuleGrammarTestCase("core root prefix", "FF", False, True),
        RuleGrammarTestCase("core family prefix", "FFR", False, True),
        RuleGrammarTestCase("one core digit prefix", "FFR3", False, True),
        RuleGrammarTestCase("two core digit prefix", "FFR30", False, True),
        RuleGrammarTestCase("exact core code", "FFR301", True, True),
        RuleGrammarTestCase("unpopulated core family prefix", "FFZ", False, True),
        RuleGrammarTestCase("unpopulated exact core code", "FFZ001", True, True),
        RuleGrammarTestCase("custom root prefix", "X", False, True),
        RuleGrammarTestCase("custom namespace prefix", "XDB", False, True),
        RuleGrammarTestCase("exact namespaced custom code", "XDB001", True, True),
        RuleGrammarTestCase("exact unnamespaced custom code", "X1", True, True),
        RuleGrammarTestCase("exact long custom code", "X0000001", True, True),
        RuleGrammarTestCase("empty value", "", False, False),
        RuleGrammarTestCase("non-string value", 1, False, False),
        RuleGrammarTestCase("partial core marker", "S", False, False),
        RuleGrammarTestCase("core selector with no family before digits", "FF1", False, False),
        RuleGrammarTestCase("core selector with too many digits", "FFR0001", False, False),
        RuleGrammarTestCase("core selector with letters after digit", "FFR3A", False, False),
        RuleGrammarTestCase("lowercase core selector", "ffr", False, False),
        RuleGrammarTestCase("lowercase custom selector", "Xdb", False, False),
        RuleGrammarTestCase("hyphenated custom selector", "XDB-001", False, False),
        RuleGrammarTestCase("underscored custom selector", "XDB_001", False, False),
        RuleGrammarTestCase("custom selector with letter after digit", "XDB1A", False, False),
    ],
    ids=lambda case: case.description,
)
def test_given_rule_spelling_when_classifying_then_applies_unified_grammar(
    test_case: RuleGrammarTestCase,
) -> None:
    assert is_rule_code(test_case.value) is test_case.expected_is_code
    assert is_rule_selector(test_case.value) is test_case.expected_is_selector


@pytest.mark.parametrize(
    "test_case",
    [
        RuleSelectorMatchTestCase("core root matches core code", "FFR301", "FF", True),
        RuleSelectorMatchTestCase("core bucket matches core code", "FFR301", "FFR3", True),
        RuleSelectorMatchTestCase("custom namespace matches nested code", "XDBX001", "XDB", True),
        RuleSelectorMatchTestCase("core root does not match custom code", "XDB001", "FF", False),
        RuleSelectorMatchTestCase("custom root does not match core code", "FFR301", "X", False),
        RuleSelectorMatchTestCase("different valid prefix does not match", "FFR301", "FFZ", False),
        RuleSelectorMatchTestCase("selector-only code is rejected", "FFR3", "FFR", False),
        RuleSelectorMatchTestCase("malformed selector is rejected", "FFR301", "ffr", False),
    ],
    ids=lambda case: case.description,
)
def test_given_code_and_selector_when_matching_then_requires_valid_prefix_spellings(
    test_case: RuleSelectorMatchTestCase,
) -> None:
    result: bool = matches_rule_selector(code=test_case.code, selector=test_case.selector)

    assert result is test_case.expected_matches
