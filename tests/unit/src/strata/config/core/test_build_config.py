"""Tests for building validated configuration from in-memory mappings."""

from __future__ import annotations

import pytest

from strata.config.core.exceptions import ConfigError, ConfigValidationError
from strata.config.core.main.build_config import build_config
from strata.config.core.models import Config
from tests.unit.src.strata.config.core._test_types import (
    InMemoryConfigBuildTestCase,
    InvalidInMemoryConfigTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        InMemoryConfigBuildTestCase(
            description="valid raw mapping is normalized",
            raw_config={"roots": ["src/pkg"], "select": ["SFL"]},
            expected_roots=("src/pkg",),
            expected_select=("SFL",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_valid_raw_mapping_when_building_then_returns_config(
    test_case: InMemoryConfigBuildTestCase,
) -> None:
    config: Config = build_config(test_case.raw_config)

    assert config.roots == test_case.expected_roots
    assert config.select == test_case.expected_select


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidInMemoryConfigTestCase(
            description="invalid selector is rejected",
            raw_config={"roots": ["src/pkg"], "select": ["BAD"]},
            expected_error_type=ConfigValidationError,
            expected_error_fragment="BAD",
        ),
        InvalidInMemoryConfigTestCase(
            description="nested roots are rejected",
            raw_config={"roots": ["src", "src/pkg"]},
            expected_error_type=ConfigError,
            expected_error_fragment="nested",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_raw_mapping_when_building_then_raises_validation_error(
    test_case: InvalidInMemoryConfigTestCase,
) -> None:
    with pytest.raises(test_case.expected_error_type) as error:
        build_config(test_case.raw_config)

    assert test_case.expected_error_fragment in str(error.value)
