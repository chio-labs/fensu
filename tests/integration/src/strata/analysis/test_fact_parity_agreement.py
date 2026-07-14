"""Fact-family parity between backends over the installed package."""

from pathlib import Path

import pytest

import strata
from tests.integration.src.strata.analysis._test_types import RepoFactParityTestCase

_: object = pytest.importorskip("strata_facts")

from tests.integration.src.strata.analysis.helpers import (  # noqa: E402
    fact_family_divergences,
)


@pytest.mark.parametrize(
    "test_case",
    [
        RepoFactParityTestCase(
            description="native fact families match python facts over the strata package",
            expected_divergent=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_installed_strata_package_when_extracting_facts_then_no_family_diverges(
    test_case: RepoFactParityTestCase,
) -> None:
    package_root: Path = Path(strata.__file__).resolve().parent

    divergent: tuple[str, ...] = fact_family_divergences(root=package_root)

    assert divergent == test_case.expected_divergent
