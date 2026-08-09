"""Tests for explicit named analyzer target configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.config.exceptions import ConfigError
from fensu.config.main.load_target_project_config import load_target_project_config
from fensu.config.models import Config
from tests.unit.src.fensu.config._test_types import (
    InvalidTargetConfigTestCase,
    TargetConfigTestCase,
)
from tests.unit.src.fensu.config.helpers import write_fensu_toml


@pytest.mark.parametrize(
    "test_case",
    [
        TargetConfigTestCase(
            description="one explicit Python target is selected automatically",
            config_text=(
                "[targets.app]\n"
                'analyzer = "python"\n'
                'roots = ["src/app"]\n'
                'tests = ["tests/app"]\n'
                'tooling = ["scripts/app"]\n'
                'select = ["FFA"]\n'
            ),
            target=None,
            expected_target="app",
            expected_roots=("src/app",),
            expected_select=("FFA",),
        ),
        TargetConfigTestCase(
            description="named selection chooses one of multiple Python targets",
            config_text=(
                "[targets.api]\n"
                'analyzer = "python"\n'
                'roots = ["src/api"]\n'
                'select = ["FFA"]\n'
                "[targets.worker]\n"
                'analyzer = "python"\n'
                'root = "."\n'
                'roots = ["src/worker"]\n'
                'select = ["FFL"]\n'
            ),
            target="worker",
            expected_target="worker",
            expected_roots=("src/worker",),
            expected_select=("FFL",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_explicit_targets_when_loading_then_selects_flat_python_config(
    tmp_path: Path, test_case: TargetConfigTestCase
) -> None:
    write_fensu_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_target_project_config(start=tmp_path, target=test_case.target).config

    assert config.analyzer == "python"
    assert config.target == test_case.expected_target
    assert config.target_root == "."
    assert config.roots == test_case.expected_roots
    assert config.select == test_case.expected_select


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidTargetConfigTestCase(
            description="targets must be a table",
            config_text="targets = []\n",
            target=None,
            expected_error_fragment="targets must be a table of named targets",
        ),
        InvalidTargetConfigTestCase(
            description="targets table must not be empty",
            config_text="targets = {}\n",
            target=None,
            expected_error_fragment="must define at least one named target",
        ),
        InvalidTargetConfigTestCase(
            description="named target must be a table",
            config_text='targets = { app = "python" }\n',
            target=None,
            expected_error_fragment="target app must be a table",
        ),
        InvalidTargetConfigTestCase(
            description="legacy and explicit configuration cannot be mixed",
            config_text=(
                'roots = ["src/legacy"]\n[targets.app]\nanalyzer = "python"\nroots = ["src/app"]\n'
            ),
            target=None,
            expected_error_fragment="cannot be mixed with legacy top-level config keys: roots",
        ),
        InvalidTargetConfigTestCase(
            description="target analyzer is required",
            config_text='[targets.app]\nroots = ["src/app"]\n',
            target=None,
            expected_error_fragment="targets.app.analyzer must be a non-empty string",
        ),
        InvalidTargetConfigTestCase(
            description="unknown analyzers fail closed",
            config_text=('[targets.web]\nanalyzer = "svelte"\nroots = ["src/web"]\n'),
            target=None,
            expected_error_fragment="Unknown analyzer for target web: svelte",
        ),
        InvalidTargetConfigTestCase(
            description="non-dot target roots fail closed",
            config_text=(
                '[targets.app]\nanalyzer = "python"\nroot = "backend"\nroots = ["src/app"]\n'
            ),
            target=None,
            expected_error_fragment='only root = "." is supported',
        ),
        InvalidTargetConfigTestCase(
            description="unknown target-local fields are rejected",
            config_text=(
                '[targets.app]\nanalyzer = "python"\nroots = ["src/app"]\nlanguage = "python"\n'
            ),
            target=None,
            expected_error_fragment="Unknown targets.app config key(s): language",
        ),
        InvalidTargetConfigTestCase(
            description="unknown requested target names are rejected",
            config_text=('[targets.app]\nanalyzer = "python"\nroots = ["src/app"]\n'),
            target="missing",
            expected_error_fragment="Unknown target name: missing",
        ),
        InvalidTargetConfigTestCase(
            description="multiple targets require explicit selection",
            config_text=(
                "[targets.api]\n"
                'analyzer = "python"\n'
                'roots = ["src/api"]\n'
                "[targets.worker]\n"
                'analyzer = "python"\n'
                'roots = ["src/worker"]\n'
            ),
            target=None,
            expected_error_fragment="select one with --target TARGET",
        ),
        InvalidTargetConfigTestCase(
            description="legacy config rejects named target selection",
            config_text='roots = ["src/app"]\n',
            target="app",
            expected_error_fragment="Unknown target name: app",
        ),
        InvalidTargetConfigTestCase(
            description="unselected target must define non-empty roots",
            config_text=(
                "[targets.valid]\n"
                'analyzer = "python"\n'
                'roots = ["src/valid"]\n'
                "[targets.invalid]\n"
                'analyzer = "python"\n'
                "roots = []\n"
            ),
            target="valid",
            expected_error_fragment="must define at least one root in roots",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_explicit_targets_when_loading_then_fails_closed(
    tmp_path: Path, test_case: InvalidTargetConfigTestCase
) -> None:
    write_fensu_toml(root=tmp_path, contents=test_case.config_text)

    with pytest.raises(ConfigError) as error:
        load_target_project_config(start=tmp_path, target=test_case.target)

    assert test_case.expected_error_fragment in str(error.value)
