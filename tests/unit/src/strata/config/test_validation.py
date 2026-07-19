"""Tests for strict config schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.config.exceptions import ConfigError, ConfigValidationError
from strata.config.main.load_config import load_config
from strata.config.models import Config
from tests.unit.src.strata.config._test_types import (
    InvalidConfigTestCase,
    RuleSelectorConfigTestCase,
)
from tests.unit.src.strata.config.helpers import write_strata_toml


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidConfigTestCase(
            description="memory preference must be a table",
            config_text='roots = ["src/pkg"]\nmemory = true\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="memory must be a table",
        ),
        InvalidConfigTestCase(
            description="memory table rejects unknown options",
            config_text='roots = ["src/pkg"]\n[memory]\nbackend = "local"\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="Unknown memory config key(s): backend",
        ),
        InvalidConfigTestCase(
            description="legacy memory activation has no compatibility alias",
            config_text='roots = ["src/pkg"]\n[memory]\nenabled = true\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="Unknown memory config key(s): enabled",
        ),
        InvalidConfigTestCase(
            description="experimental memory preference must be boolean",
            config_text='roots = ["src/pkg"]\n[experimental]\nmemory = 1\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="experimental.memory must be a boolean",
        ),
        InvalidConfigTestCase(
            description="memory tasks preference must be a table",
            config_text='roots = ["src/pkg"]\n[memory]\ntasks = 7\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="memory.tasks must be a table",
        ),
        InvalidConfigTestCase(
            description="memory tasks table rejects unknown options",
            config_text='roots = ["src/pkg"]\n[memory.tasks]\narchive = 7\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="Unknown memory.tasks config key(s): archive",
        ),
        InvalidConfigTestCase(
            description="memory task archive age must be an integer",
            config_text=('roots = ["src/pkg"]\n[memory.tasks]\narchive_after_days = "7"\n'),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="archive_after_days must be an integer",
        ),
        InvalidConfigTestCase(
            description="memory task archive age rejects boolean integers",
            config_text='roots = ["src/pkg"]\n[memory.tasks]\narchive_after_days = true\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="archive_after_days must be an integer",
        ),
        InvalidConfigTestCase(
            description="memory task archive age must be non-negative",
            config_text='roots = ["src/pkg"]\n[memory.tasks]\narchive_after_days = -1\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="archive_after_days must be non-negative",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_memory_preference_when_loading_then_raises_validation_error(
    tmp_path: Path, test_case: InvalidConfigTestCase
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    with pytest.raises(test_case.expected_error_type) as error:
        load_config(tmp_path)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidConfigTestCase(
            description="evaluation must be a table",
            config_text='roots = ["src/pkg"]\nevaluation = ["src/**"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="evaluation must be a table",
        ),
        InvalidConfigTestCase(
            description="evaluation rejects unknown keys",
            config_text='roots = ["src/pkg"]\n[evaluation]\npaths = ["src/**"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="Unknown evaluation config key(s): paths",
        ),
        InvalidConfigTestCase(
            description="evaluation include must be a list",
            config_text='roots = ["src/pkg"]\n[evaluation]\ninclude = "src/**"\n',
            expected_error_type=ConfigError,
            expected_error_fragment="evaluation.include must be a list",
        ),
        InvalidConfigTestCase(
            description="evaluation exclude list must not be empty",
            config_text='roots = ["src/pkg"]\n[evaluation]\nexclude = []\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="evaluation.exclude must not be empty",
        ),
        InvalidConfigTestCase(
            description="evaluation patterns must be nonempty strings",
            config_text='roots = ["src/pkg"]\n[evaluation]\ninclude = [""]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="evaluation.include must contain non-empty strings",
        ),
        InvalidConfigTestCase(
            description="evaluation rejects absolute POSIX glob",
            config_text='roots = ["src/pkg"]\n[evaluation]\ninclude = ["/src/**"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="repository-relative POSIX glob",
        ),
        InvalidConfigTestCase(
            description="evaluation rejects backslash glob",
            config_text='roots = ["src/pkg"]\n[evaluation]\ninclude = ["src\\\\pkg\\\\**"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="repository-relative POSIX glob",
        ),
        InvalidConfigTestCase(
            description="evaluation rejects current-directory glob",
            config_text='roots = ["src/pkg"]\n[evaluation]\ninclude = ["./src/**"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="repository-relative POSIX glob",
        ),
        InvalidConfigTestCase(
            description="evaluation rejects parent-directory glob",
            config_text='roots = ["src/pkg"]\n[evaluation]\ninclude = ["../src/**"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="repository-relative POSIX glob",
        ),
        InvalidConfigTestCase(
            description="evaluation rejects question-mark glob",
            config_text='roots = ["src/pkg"]\n[evaluation]\ninclude = ["src/?/file.py"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="repository-relative POSIX glob",
        ),
        InvalidConfigTestCase(
            description="evaluation rejects character-class glob",
            config_text='roots = ["src/pkg"]\n[evaluation]\ninclude = ["src/[ab]/file.py"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="repository-relative POSIX glob",
        ),
        InvalidConfigTestCase(
            description="evaluation rejects adjacent globstars",
            config_text='roots = ["src/pkg"]\n[evaluation]\ninclude = ["src/**/**/file.py"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="repository-relative POSIX glob",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_evaluation_config_when_loading_then_raises_validation_error(
    tmp_path: Path, test_case: InvalidConfigTestCase
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    with pytest.raises(test_case.expected_error_type) as error:
        load_config(tmp_path)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidConfigTestCase(
            description="threshold override requires paths",
            config_text=(
                'roots = ["src/pkg"]\n[[threshold_overrides]]\npaths = []\n'
                'reason = "required"\nthresholds = { max_role_depth = 2 }\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="paths must not be empty",
        ),
        InvalidConfigTestCase(
            description="threshold override requires a nonempty reason",
            config_text=(
                'roots = ["src/pkg"]\n[[threshold_overrides]]\npaths = ["src/**/*.py"]\n'
                'reason = "  "\nthresholds = { max_role_depth = 2 }\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="reason",
        ),
        InvalidConfigTestCase(
            description="threshold override requires nonempty inline thresholds",
            config_text=(
                'roots = ["src/pkg"]\n[[threshold_overrides]]\npaths = ["src/**/*.py"]\n'
                'reason = "required"\nthresholds = {}\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="non-empty inline table",
        ),
        InvalidConfigTestCase(
            description="threshold override rejects unknown entry keys",
            config_text=(
                'roots = ["src/pkg"]\n[[threshold_overrides]]\npaths = ["src/**/*.py"]\n'
                'reason = "required"\nnote = "extra"\n'
                "thresholds = { max_role_depth = 2 }\n"
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="only paths, thresholds, and reason",
        ),
        InvalidConfigTestCase(
            description="threshold override rejects old threshold names",
            config_text=(
                'roots = ["src/pkg"]\n[[threshold_overrides]]\npaths = ["src/**/*.py"]\n'
                'reason = "required"\nthresholds = { max_flat_main_modules = 30 }\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="max_flat_main_modules",
        ),
        InvalidConfigTestCase(
            description="threshold override rejects traversal glob",
            config_text=(
                'roots = ["src/pkg"]\n[[threshold_overrides]]\npaths = ["../src/**/*.py"]\n'
                'reason = "required"\nthresholds = { max_role_depth = 2 }\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="repository-relative POSIX glob",
        ),
        InvalidConfigTestCase(
            description="threshold override rejects unsupported glob syntax",
            config_text=(
                'roots = ["src/pkg"]\n[[threshold_overrides]]\npaths = ["src/?/main.py"]\n'
                'reason = "required"\nthresholds = { max_role_depth = 2 }\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="repository-relative POSIX glob",
        ),
        InvalidConfigTestCase(
            description="threshold override rejects non-normalized relative glob",
            config_text=(
                'roots = ["src/pkg"]\n[[threshold_overrides]]\npaths = ["./src/**/*.py"]\n'
                'reason = "required"\nthresholds = { max_role_depth = 2 }\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="repository-relative POSIX glob",
        ),
        InvalidConfigTestCase(
            description="threshold override rejects redundant adjacent globstars",
            config_text=(
                'roots = ["src/pkg"]\n[[threshold_overrides]]\n'
                'paths = ["src/**/**/main/*.py"]\nreason = "required"\n'
                "thresholds = { max_role_depth = 2 }\n"
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="repository-relative POSIX glob",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_threshold_override_when_loading_then_raises_validation_error(
    tmp_path: Path, test_case: InvalidConfigTestCase
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    with pytest.raises(test_case.expected_error_type) as error:
        load_config(tmp_path)

    assert test_case.expected_error_fragment in str(error.value)


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
            description="custom namespace rule exception selector is rejected",
            config_text=(
                'roots = ["src/pkg"]\n[[rule_exceptions]]\nrule = "XDB"\n'
                'path = "src/pkg/a.py"\nsymbols = ["run"]\nreason = "required"\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="exact rule code",
        ),
        InvalidConfigTestCase(
            description="legacy custom rule exception code is rejected",
            config_text=(
                'roots = ["src/pkg"]\n[[rule_exceptions]]\nrule = "XDB-001"\n'
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
            description="empty symbols do not masquerade as file level scope",
            config_text=(
                'roots = ["src/pkg"]\n[[rule_exceptions]]\nrule = "SFS120"\n'
                'path = "src/pkg/a.py"\nsymbols = []\nreason = "required"\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="omit symbols for a file-level exception",
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
        InvalidConfigTestCase(
            description="duplicate file level exception is rejected",
            config_text=(
                'roots = ["src/pkg"]\n'
                '[[rule_exceptions]]\nrule = "SFR307"\npath = "src/pkg/a.py"\nreason = "first"\n'
                '[[rule_exceptions]]\nrule = "SFR307"\npath = "src/pkg/a.py"\nreason = "second"\n'
            ),
            expected_error_type=ConfigValidationError,
            expected_error_fragment="Duplicate file-level",
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
            description="skills preference must be a table",
            config_text='roots = ["src/pkg"]\nskills = "project"\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="skills must be a table",
        ),
        InvalidConfigTestCase(
            description="skills table rejects unknown options",
            config_text='roots = ["src/pkg"]\n[skills]\nidentity = "project"\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="identity",
        ),
        InvalidConfigTestCase(
            description="skills name must be a string",
            config_text='roots = ["src/pkg"]\n[skills]\nname = 3\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="skills.name",
        ),
        InvalidConfigTestCase(
            description="skills name must not be blank",
            config_text='roots = ["src/pkg"]\n[skills]\nname = "  "\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="non-empty string",
        ),
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
            description="cache preference must be a table",
            config_text='roots = ["src/pkg"]\ncache = false\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="cache must be a table",
        ),
        InvalidConfigTestCase(
            description="cache table rejects unknown options",
            config_text='roots = ["src/pkg"]\n[cache]\nenable = false\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="enable",
        ),
        InvalidConfigTestCase(
            description="cache enabled preference must be boolean",
            config_text='roots = ["src/pkg"]\n[cache]\nenabled = "yes"\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="boolean",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_cache_preference_when_loading_then_raises_validation_error(
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
            description="warn must be a list",
            config_text='roots = ["src/pkg"]\nwarn = "SFR"\n',
            expected_error_type=ConfigError,
            expected_error_fragment="warn",
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
        InvalidConfigTestCase(
            description="invalid warn selector is rejected",
            config_text='roots = ["src/pkg"]\nwarn = ["NOPE"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="NOPE",
        ),
        InvalidConfigTestCase(
            description="legacy lowercase custom selector is rejected",
            config_text='roots = ["src/pkg"]\nselect = ["Xdb"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="Xdb",
        ),
        InvalidConfigTestCase(
            description="legacy hyphenated custom selector is rejected",
            config_text='roots = ["src/pkg"]\nselect = ["XDB-001"]\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="XDB-001",
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
        RuleSelectorConfigTestCase(
            description="core buckets and custom namespaces are valid selectors",
            config_text=(
                'roots = ["src/pkg"]\nselect = ["SF", "SFR", "SFR3", "SFZ001", "XDB"]\n'
                'warn = ["SFS102", "XAD"]\n'
                'ignore = ["SFR30", "XDB001"]\n'
            ),
            expected_select=("SF", "SFR", "SFR3", "SFZ001", "XDB"),
            expected_warn=("SFS102", "XAD"),
            expected_ignore=("SFR30", "XDB001"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_valid_prefix_selectors_when_loading_then_preserves_spellings(
    tmp_path: Path,
    test_case: RuleSelectorConfigTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)

    assert config.select == test_case.expected_select
    assert config.warn == test_case.expected_warn
    assert config.ignore == test_case.expected_ignore


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
        InvalidConfigTestCase(
            description="global threshold rejects boolean integers",
            config_text='roots = ["src/pkg"]\n[thresholds]\nmax_statements = true\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="integer",
        ),
        InvalidConfigTestCase(
            description="role threshold rejects boolean integers",
            config_text='roots = ["src/pkg"]\n[roles.main]\nmax_statements = false\n',
            expected_error_type=ConfigValidationError,
            expected_error_fragment="integer",
        ),
        InvalidConfigTestCase(
            description="threshold override rejects boolean integers",
            config_text=(
                'roots = ["src/pkg"]\n[[threshold_overrides]]\npaths = ["src/**/*.py"]\n'
                'reason = "required"\nthresholds = { max_role_depth = true }\n'
            ),
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
