"""Tests for the naming rule catalogue."""

from __future__ import annotations

import pytest

from fensu.config.models import Config
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.catalog.main.build_ruleset import build_ruleset
from fensu.rules.naming.constants import FFN_RULES
from fensu.rules.naming.types import NamingCode
from tests.unit.src.fensu.rules.naming._test_types import (
    FfnCatalogueTestCase,
    FfnSelectionTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        FfnCatalogueTestCase(
            description="naming rule catalogue matches naming code enum",
            expected_codes=tuple(code.value for code in NamingCode),
            expected_unique_count=len(NamingCode),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_naming_rule_catalogue_when_reading_codes_then_matches_naming_code_enum(
    test_case: FfnCatalogueTestCase,
) -> None:
    codes: tuple[str, ...] = tuple(rule.code for rule in FFN_RULES)

    assert codes == test_case.expected_codes
    assert len(set(codes)) == test_case.expected_unique_count


@pytest.mark.parametrize(
    "test_case",
    [
        FfnSelectionTestCase(
            description="exact predicate rule selection",
            select=("FFN002",),
            ignore=(),
            expected_codes=("FFN002",),
        ),
        FfnSelectionTestCase(
            description="exact value rule selection",
            select=("FFN003",),
            ignore=(),
            expected_codes=("FFN003",),
        ),
        FfnSelectionTestCase(
            description="exact iterator rule selection",
            select=("FFN004",),
            ignore=(),
            expected_codes=("FFN004",),
        ),
        FfnSelectionTestCase(
            description="family selection includes every naming behavior",
            select=("FFN",),
            ignore=(),
            expected_codes=("FFN001", "FFN002", "FFN003", "FFN004"),
        ),
        FfnSelectionTestCase(
            description="exact predicate ignore removes only predicate behavior",
            select=("FFN",),
            ignore=("FFN002",),
            expected_codes=("FFN001", "FFN003", "FFN004"),
        ),
        FfnSelectionTestCase(
            description="exact value ignore removes only value behavior",
            select=("FFN",),
            ignore=("FFN003",),
            expected_codes=("FFN001", "FFN002", "FFN004"),
        ),
        FfnSelectionTestCase(
            description="exact iterator ignore removes only iterator behavior",
            select=("FFN",),
            ignore=("FFN004",),
            expected_codes=("FFN001", "FFN002", "FFN003"),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_naming_selectors_when_building_ruleset_then_composes_exact_behaviors(
    test_case: FfnSelectionTestCase,
) -> None:
    ruleset: tuple[RuleSpec, ...] = build_ruleset(
        config=Config(
            roots=("src/pkg",),
            tests=(),
            select=test_case.select,
            ignore=test_case.ignore,
        )
    )

    assert tuple(rule.code for rule in ruleset) == test_case.expected_codes
