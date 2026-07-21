"""Installed-source discovery tests for custom-rule authoring guidance."""

from __future__ import annotations

from pathlib import Path

import pytest

import fensu.rules.exemplars as exemplars
from tests.integration.src.fensu.rules.exemplars._test_types import AuthoringIndexTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        AuthoringIndexTestCase(
            description="installed index names examples rule testing and configuration",
            section_names=(
                "## Start Here",
                "## Minimal Rule",
                "## Test The Real Pipeline",
                "## Configure Discovery",
            ),
            expected_counts=(1, 1, 1, 1),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_installed_fensu_when_discovering_authoring_then_index_is_complete(
    test_case: AuthoringIndexTestCase,
) -> None:
    index_path: Path = Path(exemplars.__file__).with_name("AUTHORING.md")

    content: str = index_path.read_text(encoding="utf-8")

    assert tuple(content.count(section) for section in test_case.section_names) == (
        test_case.expected_counts
    )
