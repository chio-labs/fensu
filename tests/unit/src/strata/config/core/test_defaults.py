"""Tests for config defaults and normalization."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.config.core.main.load_config import load_config
from strata.config.core.models import Config
from strata.rules.authoring.types import Threshold
from tests.unit.src.strata.config.core._test_types import (
    ConfigContractTestCase,
    ConfigDefaultsTestCase,
    ConfigListFieldTestCase,
    ConfigThresholdTestCase,
)
from tests.unit.src.strata.config.core.helpers import write_strata_toml


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigDefaultsTestCase(
            description="no optional fields applies shipped defaults",
            config_text='roots = ["src/pkg"]\n',
            expected_roots=("src/pkg",),
            expected_tests=("tests",),
            expected_tooling=(),
            expected_threshold_name="max_statements",
            expected_threshold_value=40,
            expected_role_name=None,
            expected_role_threshold_name=None,
            expected_role_threshold_value=None,
        ),
        ConfigDefaultsTestCase(
            description="multiple independent roots are kept",
            config_text='roots = ["src/pkg_a", "src/pkg_b"]\ntests = ["test_suite"]\n',
            expected_roots=("src/pkg_a", "src/pkg_b"),
            expected_tests=("test_suite",),
            expected_tooling=(),
            expected_threshold_name="max_file_lines",
            expected_threshold_value=2000,
            expected_role_name=None,
            expected_role_threshold_name=None,
            expected_role_threshold_value=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_valid_config_when_loading_then_applies_defaults(
    tmp_path: Path,
    test_case: ConfigDefaultsTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)
    threshold: Threshold = Threshold(test_case.expected_threshold_name)

    assert config.roots == test_case.expected_roots
    assert config.tests == test_case.expected_tests
    assert config.tooling == test_case.expected_tooling
    assert config.thresholds[threshold] == test_case.expected_threshold_value


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigListFieldTestCase(
            description="tests override is normalized",
            config_text='roots = ["src/pkg"]\ntests = ["test_suite"]\n',
            expected_field_name="tests",
            expected_value=("test_suite",),
        ),
        ConfigListFieldTestCase(
            description="tooling override is normalized",
            config_text='roots = ["src/pkg"]\ntooling = ["scripts", "tools"]\n',
            expected_field_name="tooling",
            expected_value=("scripts", "tools"),
        ),
        ConfigListFieldTestCase(
            description="select override is normalized",
            config_text='roots = ["src/pkg"]\nselect = ["SFL", "XWH001"]\n',
            expected_field_name="select",
            expected_value=("SFL", "XWH001"),
        ),
        ConfigListFieldTestCase(
            description="custom family selector is accepted",
            config_text='roots = ["src/pkg"]\nselect = ["X"]\n',
            expected_field_name="select",
            expected_value=("X",),
        ),
        ConfigListFieldTestCase(
            description="ignore override is normalized",
            config_text='roots = ["src/pkg"]\nignore = ["SFX002"]\n',
            expected_field_name="ignore",
            expected_value=("SFX002",),
        ),
        ConfigListFieldTestCase(
            description="rule paths override is normalized",
            config_text='roots = ["src/pkg"]\nrule_paths = ["strata_rules"]\n',
            expected_field_name="rule_paths",
            expected_value=("strata_rules",),
        ),
        ConfigListFieldTestCase(
            description="rule modules override is normalized",
            config_text='roots = ["src/pkg"]\nrule_modules = ["pkg.strata_rules"]\n',
            expected_field_name="rule_modules",
            expected_value=("pkg.strata_rules",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_list_field_overrides_when_loading_then_normalizes_to_tuple(
    tmp_path: Path,
    test_case: ConfigListFieldTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)

    assert getattr(config, test_case.expected_field_name) == test_case.expected_value


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigThresholdTestCase(
            description="all threshold enum members are present by default",
            config_text='roots = ["src/pkg"]\n',
            expected_threshold_name="max_arguments",
            expected_threshold_value=10,
        ),
        ConfigThresholdTestCase(
            description="global threshold override is applied",
            config_text='roots = ["src/pkg"]\n[thresholds]\nmax_statements = 50\n',
            expected_threshold_name="max_statements",
            expected_threshold_value=50,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_threshold_config_when_loading_then_thresholds_are_complete_and_overridden(
    tmp_path: Path,
    test_case: ConfigThresholdTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)
    threshold: Threshold = Threshold(test_case.expected_threshold_name)

    assert set(config.thresholds) == set(Threshold)
    assert config.thresholds[threshold] == test_case.expected_threshold_value


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigDefaultsTestCase(
            description="role threshold override is stored separately from global defaults",
            config_text=(
                'roots = ["src/pkg"]\n'
                "[thresholds]\nmax_statements = 50\n"
                "[roles.entry]\nmax_statements = 30\n"
            ),
            expected_roots=("src/pkg",),
            expected_tests=("tests",),
            expected_tooling=(),
            expected_threshold_name="max_statements",
            expected_threshold_value=50,
            expected_role_name="entry",
            expected_role_threshold_name="max_statements",
            expected_role_threshold_value=30,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_role_threshold_override_when_loading_then_global_and_role_values_apply(
    tmp_path: Path,
    test_case: ConfigDefaultsTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)
    threshold: Threshold = Threshold(test_case.expected_threshold_name)
    role_threshold: Threshold = Threshold(test_case.expected_role_threshold_name or "")

    assert config.thresholds[threshold] == test_case.expected_threshold_value
    assert config.role_thresholds[test_case.expected_role_name or ""][role_threshold] == (
        test_case.expected_role_threshold_value
    )


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigContractTestCase(
            description="default validator contract is present",
            config_text='roots = ["src/pkg"]\n',
            expected_pattern="validate_*",
            expected_behavior="no-return",
        ),
        ConfigContractTestCase(
            description="user contract merges with defaults",
            config_text='roots = ["src/pkg"]\n[contracts]\n"write_*" = "no-return"\n',
            expected_pattern="write_*",
            expected_behavior="no-return",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_contract_config_when_loading_then_defaults_and_user_contracts_apply(
    tmp_path: Path,
    test_case: ConfigContractTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)

    assert config.contracts[test_case.expected_pattern] == test_case.expected_behavior
    assert config.contracts["enforce_*"] == "no-return"
