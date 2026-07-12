"""Tests distinguishing blank prompt defaults from end-of-input."""

from __future__ import annotations

import pytest

from strata.scaffolding.core.exceptions import InitError
from tests.unit.src.strata.scaffolding.core._test_types import (
    PromptDefaultTestCase,
    PromptEofTestCase,
)
from tests.unit.src.strata.scaffolding.core.helpers import invoke_prompt


@pytest.mark.parametrize(
    "test_case",
    [
        PromptDefaultTestCase(
            description="blank generic confirmation accepts yes default",
            prompt_kind="generic",
            expected_result=True,
        ),
        PromptDefaultTestCase(
            description="blank layout confirmation accepts layout default",
            prompt_kind="layout",
            expected_result=True,
        ),
        PromptDefaultTestCase(
            description="blank root selection accepts every candidate",
            prompt_kind="root",
            expected_result=("src/alpha", "src/beta"),
        ),
        PromptDefaultTestCase(
            description="blank project name accepts normalized repository default",
            prompt_kind="name",
            expected_result="my_project",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_explicit_blank_line_when_prompting_then_uses_displayed_default(
    test_case: PromptDefaultTestCase,
) -> None:
    result: bool | tuple[str, ...] | str = invoke_prompt(
        prompt_kind=test_case.prompt_kind, input_text="\n"
    )

    assert result == test_case.expected_result


@pytest.mark.parametrize(
    "test_case",
    [
        PromptEofTestCase(
            description="generic confirmation EOF is not accepted as blank",
            prompt_kind="generic",
            expected_error_type=InitError,
            expected_error_fragment="Unexpected EOF while reading yes/no confirmation",
        ),
        PromptEofTestCase(
            description="layout confirmation EOF is not accepted as blank",
            prompt_kind="layout",
            expected_error_type=InitError,
            expected_error_fragment="Unexpected EOF while reading layout confirmation",
        ),
        PromptEofTestCase(
            description="root selection EOF is not accepted as blank",
            prompt_kind="root",
            expected_error_type=InitError,
            expected_error_fragment="Unexpected EOF while reading runtime root selection",
        ),
        PromptEofTestCase(
            description="project name EOF is not accepted as blank",
            prompt_kind="name",
            expected_error_type=InitError,
            expected_error_fragment="Unexpected EOF while reading project name",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_end_of_input_when_prompting_then_raises_instead_of_using_default(
    test_case: PromptEofTestCase,
) -> None:
    with pytest.raises(test_case.expected_error_type) as error:
        invoke_prompt(prompt_kind=test_case.prompt_kind, input_text="")

    assert test_case.expected_error_fragment in str(error.value)
