"""Tests for semantic CLI styling."""

from __future__ import annotations

import pytest

from strata.reporting.core.classes.cli_style import CliStyle
from tests.unit.src.strata.reporting.core.classes._test_types import CliStyleTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        CliStyleTestCase(
            description="color mode applies the init semantic theme",
            use_color=True,
            expected_rendered=(
                "\033[1;36m-->\033[0m|"
                "\033[1mHeader\033[0m|"
                "\033[1mvalue\033[0m|"
                "\033[1msrc/pkg\033[0m|"
                "\033[2mpyproject signal\033[0m|"
                "\033[2m[Y/n]\033[0m|"
                "\033[2mnone detected\033[0m|"
                "\033[1;32mWrote strata.toml\033[0m|"
                "\033[38;5;208mSFA\033[0m|"
                "\033[1;38;5;208m12 faults\033[0m|"
                "\033[1;36mdocs.stratalint.com/adoption\033[0m"
            ),
        ),
        CliStyleTestCase(
            description="plain mode returns every semantic value unchanged",
            use_color=False,
            expected_rendered=(
                "-->|Header|value|src/pkg|pyproject signal|[Y/n]|none detected|"
                "Wrote strata.toml|SFA|12 faults|docs.stratalint.com/adoption"
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_color_setting_when_styling_cli_text_then_returns_exact_semantic_strings(
    test_case: CliStyleTestCase,
) -> None:
    style: CliStyle = CliStyle(use_color=test_case.use_color)

    rendered: str = "|".join(
        (
            style.header_marker(),
            style.header_text("Header"),
            style.value("value"),
            style.path("src/pkg"),
            style.provenance("pyproject signal"),
            style.hint("[Y/n]"),
            style.absent("none detected"),
            style.success("Wrote strata.toml"),
            style.family_fault_code("SFA"),
            style.fault_count("12 faults"),
            style.link("docs.stratalint.com/adoption"),
        )
    )

    assert rendered == test_case.expected_rendered
