"""Parser validity agreement between backends over the installed package."""

from pathlib import Path

import pytest

import strata
from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from tests.integration.src.strata.analysis._test_types import RepoParseAgreementTestCase

_: object = pytest.importorskip(NATIVE_FACT_MODULE_NAME)

from tests.integration.src.strata.analysis.helpers import (  # noqa: E402
    parse_validity_divergences,
)


@pytest.mark.parametrize(
    "test_case",
    [
        RepoParseAgreementTestCase(
            description="native strict-parse validity matches ast.parse over the strata package",
            expected_divergent=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_installed_strata_package_when_checking_both_parsers_then_no_file_diverges(
    test_case: RepoParseAgreementTestCase,
) -> None:
    package_root: Path = Path(strata.__file__).resolve().parent

    divergent: tuple[str, ...] = parse_validity_divergences(root=package_root)

    assert divergent == test_case.expected_divergent
