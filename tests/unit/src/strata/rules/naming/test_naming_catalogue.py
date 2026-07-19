"""Tests for the naming rule catalogue."""

from __future__ import annotations

import pytest

from strata.config.models import Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.main.build_ruleset import build_ruleset
from strata.rules.naming.constants import SFN_RULES
from strata.rules.naming.types import NamingCode
from tests.unit.src.strata.rules.naming._test_types import (
    SfnCatalogueTestCase,
    SfnSelectionTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        SfnCatalogueTestCase(
            description="naming rule catalogue matches naming code enum",
            expected_codes=tuple(code.value for code in NamingCode),
            expected_unique_count=len(NamingCode),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_naming_rule_catalogue_when_reading_codes_then_matches_naming_code_enum(
    test_case: SfnCatalogueTestCase,
) -> None:
    codes: tuple[str, ...] = tuple(rule.code for rule in SFN_RULES)

    assert codes == test_case.expected_codes
    assert len(set(codes)) == test_case.expected_unique_count


@pytest.mark.parametrize(
    "test_case",
    [
        SfnSelectionTestCase(
            description="exact predicate rule selection",
            select=("SFN002",),
            ignore=(),
            expected_codes=("SFN002",),
        ),
        SfnSelectionTestCase(
            description="exact value rule selection",
            select=("SFN003",),
            ignore=(),
            expected_codes=("SFN003",),
        ),
        SfnSelectionTestCase(
            description="exact iterator rule selection",
            select=("SFN004",),
            ignore=(),
            expected_codes=("SFN004",),
        ),
        SfnSelectionTestCase(
            description="family selection includes every naming behavior",
            select=("SFN",),
            ignore=(),
            expected_codes=("SFN001", "SFN002", "SFN003", "SFN004"),
        ),
        SfnSelectionTestCase(
            description="exact predicate ignore removes only predicate behavior",
            select=("SFN",),
            ignore=("SFN002",),
            expected_codes=("SFN001", "SFN003", "SFN004"),
        ),
        SfnSelectionTestCase(
            description="exact value ignore removes only value behavior",
            select=("SFN",),
            ignore=("SFN003",),
            expected_codes=("SFN001", "SFN002", "SFN004"),
        ),
        SfnSelectionTestCase(
            description="exact iterator ignore removes only iterator behavior",
            select=("SFN",),
            ignore=("SFN004",),
            expected_codes=("SFN001", "SFN002", "SFN003"),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_naming_selectors_when_building_ruleset_then_composes_exact_behaviors(
    test_case: SfnSelectionTestCase,
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
