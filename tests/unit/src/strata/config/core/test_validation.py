"""Tests for strict config schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.config.core.exceptions import ConfigError, ConfigValidationError
from strata.config.core.main.load_config import load_config
from tests.unit.src.strata.config.core._test_types import InvalidConfigTestCase
from tests.unit.src.strata.config.core.helpers import write_strata_toml


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidConfigTestCase(
            description="family rule exception selector is rejected",
            config_text=(
                'roots = ["src/pkg"]\n[[rule_exceptions]]\nrule = "SFS"\n'
                'path = "src/pkg/a.py"\nsymbols = ["run"]\nreason = "required"\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="exact rule code",
        ),
        InvalidConfigTestCase(
            description="glob rule exception path is rejected",
            config_text=(
                'roots = ["src/pkg"]\n[[rule_exceptions]]\nrule = "SFS120"\n'
                'path = "src/pkg/*.py"\nsymbols = ["run"]\nreason = "required"\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="exact repository-relative",
        ),
        InvalidConfigTestCase(
            description="path only rule exception is rejected",
            config_text=(
                'roots = ["src/pkg"]\n[[rule_exceptions]]\nrule = "SFS120"\n'
                'path = "src/pkg/a.py"\nreason = "required"\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="only rule, path, symbols, and reason",
        ),
        InvalidConfigTestCase(
            description="empty rule exception reason is rejected",
            config_text=(
                'roots = ["src/pkg"]\n[[rule_exceptions]]\nrule = "SFS120"\n'
                'path = "src/pkg/a.py"\nsymbols = ["run"]\nreason = "   "\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="reason",
        ),
        InvalidConfigTestCase(
            description="malformed qualified symbol is rejected",
            config_text=(
                'roots = ["src/pkg"]\n[[rule_exceptions]]\nrule = "SFS120"\n'
                'path = "src/pkg/a.py"\nsymbols = ["outer.inner.deep"]\nreason = "required"\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="Malformed",
        ),
        InvalidConfigTestCase(
            description="duplicate rule path symbol exception is rejected",
            config_text=(
                'roots = ["src/pkg"]\n'
                '[[rule_exceptions]]\nrule = "SFS120"\npath = "src/pkg/a.py"\n'
                'symbols = ["run"]\nreason = "first"\n'
                '[[rule_exceptions]]\nrule = "SFS120"\npath = "src/pkg/a.py"\n'
                'symbols = ["run"]\nreason = "second"\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="Duplicate",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_rule_exception_when_loading_then_raises_validation_error(
    tmp_path: Path,
    test_case: InvalidConfigTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    with pytest.raises(test_case.expected_error_type) as error:
        load_config(tmp_path)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidConfigTestCase(
            description="unknown key is rejected",
            config_text='roots = ["src/pkg"]\nrootss = ["typo"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="rootss",
        ),
        InvalidConfigTestCase(
            description="missing roots is rejected",
            config_text='select = ["SF"]\n',
            expected_error_type=ConfigError,
            expected_error_fragment="roots",
        ),
        InvalidConfigTestCase(
            description="empty roots is rejected",
            config_text="roots = []\n",
            expected_error_type=ConfigError,
            expected_error_fragment="roots",
        ),
        InvalidConfigTestCase(
            description="roots must be a list",
            config_text='roots = "src/pkg"\n',
            expected_error_type=ConfigError,
            expected_error_fragment="list of strings",
        ),
        InvalidConfigTestCase(
            description="roots must contain strings",
            config_text='roots = ["src/pkg", 3]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="non-empty strings",
        ),
        InvalidConfigTestCase(
            description="roots must not contain empty strings",
            config_text='roots = ["src/pkg", ""]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="non-empty strings",
        ),
        InvalidConfigTestCase(
            description="nested roots are rejected parent first",
            config_text='roots = ["src", "src/pkg"]\n',
            expected_error_type=ConfigError,
            expected_error_fragment="nested",
        ),
        InvalidConfigTestCase(
            description="nested roots are rejected child first",
            config_text='roots = ["src/pkg", "src"]\n',
            expected_error_type=ConfigError,
            expected_error_fragment="nested",
        ),
        InvalidConfigTestCase(
            description="duplicate roots are rejected as nested",
            config_text='roots = ["src/pkg", "src/pkg"]\n',
            expected_error_type=ConfigError,
            expected_error_fragment="nested",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_roots_or_top_level_key_when_loading_then_raises_expected_error(
    tmp_path: Path,
    test_case: InvalidConfigTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    with pytest.raises(test_case.expected_error_type) as error:
        load_config(tmp_path)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidConfigTestCase(
            description="tests must be a list",
            config_text='roots = ["src/pkg"]\ntests = "tests"\n',
            expected_error_type=ConfigError,
            expected_error_fragment="tests",
        ),
        InvalidConfigTestCase(
            description="tooling must contain strings",
            config_text='roots = ["src/pkg"]\ntooling = [4]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="tooling",
        ),
        InvalidConfigTestCase(
            description="rule paths must not contain empty strings",
            config_text='roots = ["src/pkg"]\nrule_paths = [""]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="rule_paths",
        ),
        InvalidConfigTestCase(
            description="rule modules must be a list",
            config_text='roots = ["src/pkg"]\nrule_modules = "pkg.rules"\n',
            expected_error_type=ConfigError,
            expected_error_fragment="rule_modules",
        ),
        InvalidConfigTestCase(
            description="select must be a list",
            config_text='roots = ["src/pkg"]\nselect = "SFL"\n',
            expected_error_type=ConfigError,
            expected_error_fragment="select",
        ),
        InvalidConfigTestCase(
            description="ignore must contain strings",
            config_text='roots = ["src/pkg"]\nignore = [5]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="ignore",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_list_field_when_loading_then_raises_expected_error(
    tmp_path: Path,
    test_case: InvalidConfigTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    with pytest.raises(test_case.expected_error_type) as error:
        load_config(tmp_path)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidConfigTestCase(
            description="invalid select selector is rejected",
            config_text='roots = ["src/pkg"]\nselect = ["BAD"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="BAD",
        ),
        InvalidConfigTestCase(
            description="unknown core family selector is rejected",
            config_text='roots = ["src/pkg"]\nselect = ["SFZ001"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="SFZ001",
        ),
        InvalidConfigTestCase(
            description="short core code selector is rejected",
            config_text='roots = ["src/pkg"]\nselect = ["SFL1"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="SFL1",
        ),
        InvalidConfigTestCase(
            description="long core code selector is rejected",
            config_text='roots = ["src/pkg"]\nselect = ["SFL0001"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="SFL0001",
        ),
        InvalidConfigTestCase(
            description="invalid ignore selector is rejected",
            config_text='roots = ["src/pkg"]\nignore = ["NOPE"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="NOPE",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_selector_when_loading_then_raises_config_validation_error(
    tmp_path: Path,
    test_case: InvalidConfigTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    with pytest.raises(test_case.expected_error_type) as error:
        load_config(tmp_path)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidConfigTestCase(
            description="unknown threshold key is rejected",
            config_text='roots = ["src/pkg"]\n[thresholds]\nmax_statments = 10\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="max_statments",
        ),
        InvalidConfigTestCase(
            description="threshold value must be integer",
            config_text='roots = ["src/pkg"]\n[thresholds]\nmax_statements = "40"\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="integer",
        ),
        InvalidConfigTestCase(
            description="threshold value must be non-negative",
            config_text='roots = ["src/pkg"]\n[thresholds]\nmax_statements = -1\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="non-negative",
        ),
        InvalidConfigTestCase(
            description="unknown role name is rejected",
            config_text='roots = ["src/pkg"]\n[roles.service]\nmax_statements = 30\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="service",
        ),
        InvalidConfigTestCase(
            description="role threshold key is validated",
            config_text='roots = ["src/pkg"]\n[roles.entry]\nmax_statments = 30\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="max_statments",
        ),
        InvalidConfigTestCase(
            description="role threshold value must be integer",
            config_text='roots = ["src/pkg"]\n[roles.entry]\nmax_statements = "30"\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="integer",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_threshold_or_role_when_loading_then_raises_expected_error(
    tmp_path: Path,
    test_case: InvalidConfigTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    with pytest.raises(test_case.expected_error_type) as error:
        load_config(tmp_path)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidConfigTestCase(
            description="contracts must be a table",
            config_text='roots = ["src/pkg"]\ncontracts = "no-return"\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="contracts",
        ),
        InvalidConfigTestCase(
            description="contract behavior must be known",
            config_text='roots = ["src/pkg"]\n[contracts]\n"write_*" = "returns"\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="returns",
        ),
        InvalidConfigTestCase(
            description="contract behavior must be string behavior",
            config_text='roots = ["src/pkg"]\n[contracts]\n"write_*" = 3\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="write_*",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_contract_when_loading_then_raises_config_validation_error(
    tmp_path: Path,
    test_case: InvalidConfigTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    with pytest.raises(test_case.expected_error_type) as error:
        load_config(tmp_path)

    assert test_case.expected_error_fragment in str(error.value)
