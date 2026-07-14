"""Strict-parse validity agreement between the native parser and ast.parse."""

import sys
from typing import Any

import pytest

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from tests.unit.src.strata.analysis._test_types import ParseValidityTestCase
from tests.unit.src.strata.analysis.helpers import cpython_parse_validity

strata_facts: Any = pytest.importorskip(NATIVE_FACT_MODULE_NAME)


@pytest.mark.parametrize(
    "test_case",
    [
        ParseValidityTestCase(
            description="a plain module is valid for both parsers",
            source="value: int = 1\n\n\ndef read_value() -> int:\n    return value\n",
            expected_cpython_valid=True,
            expected_native_valid=True,
        ),
        ParseValidityTestCase(
            description="an unclosed f-string replacement field is invalid for both parsers",
            source='column = "amount"\ntext = f"select {column from table"\n',
            expected_cpython_valid=False,
            expected_native_valid=False,
        ),
        ParseValidityTestCase(
            description="an unterminated triple-quoted string is invalid for both parsers",
            source='text = """open\n',
            expected_cpython_valid=False,
            expected_native_valid=False,
        ),
        ParseValidityTestCase(
            description="a tab dedent inside a space block is invalid for both parsers",
            source="def f():\n    a = 1\n\tb = 2\n",
            expected_cpython_valid=False,
            expected_native_valid=False,
        ),
        ParseValidityTestCase(
            description="pep 695 type aliases are valid for both parsers",
            source="type Alias = int\n",
            expected_cpython_valid=True,
            expected_native_valid=True,
        ),
        ParseValidityTestCase(
            description="nested quote reuse in f-strings is valid for both parsers on 3.12",
            source='name = "x"\ntext = f"{"literal"}"\n',
            expected_cpython_valid=True,
            expected_native_valid=True,
        ),
        ParseValidityTestCase(
            description="return at module level parses because the oracle is ast.parse",
            source="return 1\n",
            expected_cpython_valid=True,
            expected_native_valid=True,
        ),
        ParseValidityTestCase(
            description="yield at module level parses because the oracle is ast.parse",
            source="yield 1\n",
            expected_cpython_valid=True,
            expected_native_valid=True,
        ),
        ParseValidityTestCase(
            description="await at module level parses because the oracle is ast.parse",
            source="await value\n",
            expected_cpython_valid=True,
            expected_native_valid=True,
        ),
        ParseValidityTestCase(
            description="duplicate parameters parse because the oracle is ast.parse",
            source="def f(a, a):\n    return a\n",
            expected_cpython_valid=True,
            expected_native_valid=True,
        ),
        ParseValidityTestCase(
            description="a late future import parses because the oracle is ast.parse",
            source="import os\nfrom __future__ import annotations\n",
            expected_cpython_valid=True,
            expected_native_valid=True,
        ),
        ParseValidityTestCase(
            description="an empty module is valid for both parsers",
            source="",
            expected_cpython_valid=True,
            expected_native_valid=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_syntax_fixture_when_checking_both_parsers_then_validity_matches_expectations(
    test_case: ParseValidityTestCase,
) -> None:
    cpython_valid: bool = cpython_parse_validity(test_case.source)
    native_valid: bool = (
        strata_facts.check_syntax(test_case.source, sys.version_info[0], sys.version_info[1])
        is None
    )

    assert cpython_valid is test_case.expected_cpython_valid
    assert native_valid is test_case.expected_native_valid
