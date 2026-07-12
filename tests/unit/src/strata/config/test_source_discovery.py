"""Tests for config source discovery and parsing."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from strata.config.exceptions import ConfigError
from strata.config.main.find_config import find_config_source
from strata.config.main.load_config import load_config
from strata.config.models import Config, ConfigSource
from tests.unit.src.strata.config._test_types import (
    ConfigDiscoveryTestCase,
    ConfigSourceLoadTestCase,
    InvalidConfigSourceTestCase,
    MissingConfigGuidanceTestCase,
)
from tests.unit.src.strata.config.helpers import (
    write_pyproject_toml,
    write_strata_toml,
)


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigSourceLoadTestCase(
            description="dedicated strata toml loads top-level config",
            strata_toml='roots = ["src/dedicated"]\nselect = ["SFL"]\n',
            pyproject_toml="",
            expected_roots=("src/dedicated",),
            expected_select=("SFL",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_strata_toml_when_loading_then_returns_expected_config(
    tmp_path: Path,
    test_case: ConfigSourceLoadTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.strata_toml or "")

    config: Config = load_config(tmp_path)

    assert config.roots == test_case.expected_roots
    assert config.select == test_case.expected_select


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigSourceLoadTestCase(
            description="pyproject tool strata loads nested config",
            strata_toml="",
            pyproject_toml='[tool.strata]\nroots = ["src/pyproject"]\nselect = ["SFR"]\n',
            expected_roots=("src/pyproject",),
            expected_select=("SFR",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_pyproject_tool_strata_when_loading_then_returns_expected_config(
    tmp_path: Path,
    test_case: ConfigSourceLoadTestCase,
) -> None:
    write_pyproject_toml(root=tmp_path, contents=test_case.pyproject_toml or "")

    config: Config = load_config(tmp_path)

    assert config.roots == test_case.expected_roots
    assert config.select == test_case.expected_select


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigSourceLoadTestCase(
            description="dedicated file wins silently over pyproject",
            strata_toml='roots = ["src/dedicated"]\nselect = ["SFS"]\n',
            pyproject_toml='[tool.strata]\nroots = ["src/pyproject"]\nselect = ["SFR"]\n',
            expected_roots=("src/dedicated",),
            expected_select=("SFS",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_both_sources_when_loading_then_dedicated_file_wins_silently(
    tmp_path: Path,
    test_case: ConfigSourceLoadTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.strata_toml or "")
    write_pyproject_toml(root=tmp_path, contents=test_case.pyproject_toml or "")

    with warnings.catch_warnings(record=True) as captured_warnings:
        config: Config = load_config(tmp_path)

    assert config.roots == test_case.expected_roots
    assert config.select == test_case.expected_select
    assert captured_warnings == []


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigDiscoveryTestCase(
            description="start path may be a nested file",
            start_relative_path="src/pkg/module.py",
            child_pyproject_toml=None,
            parent_strata_toml='roots = ["src/pkg"]\n',
            expected_roots=("src/pkg",),
        ),
        ConfigDiscoveryTestCase(
            description="pyproject without tool strata is skipped while walking upward",
            start_relative_path="workspace/pkg/module.py",
            child_pyproject_toml='[project]\nname = "not-strata"\n',
            parent_strata_toml='roots = ["workspace/pkg"]\n',
            expected_roots=("workspace/pkg",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_nested_start_when_loading_then_discovers_parent_config(
    tmp_path: Path,
    test_case: ConfigDiscoveryTestCase,
) -> None:
    start_path: Path = tmp_path / test_case.start_relative_path
    start_path.parent.mkdir(parents=True)
    start_path.write_text("", encoding="utf-8")
    write_strata_toml(root=tmp_path, contents=test_case.parent_strata_toml or "")
    child_pyproject: Path = start_path.parent / "pyproject.toml"
    child_pyproject.write_text(test_case.child_pyproject_toml or "", encoding="utf-8")

    config: Config = load_config(start_path)

    assert config.roots == test_case.expected_roots


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidConfigSourceTestCase(
            description="no config source raises config error",
            strata_toml=None,
            pyproject_toml=None,
            expected_error_type=ConfigError,
            expected_error_fragment="No strata config found",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_missing_source_when_loading_then_raises_config_error(
    tmp_path: Path,
    test_case: InvalidConfigSourceTestCase,
) -> None:
    with pytest.raises(test_case.expected_error_type) as error:
        load_config(tmp_path)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        MissingConfigGuidanceTestCase(
            description="missing config keeps prefix and suggests init",
            expected_prefix="No strata config found",
            expected_guidance="Run 'strata init' to create one.",
            expected_source=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_missing_source_when_loading_then_preserves_prefix_and_suggests_init(
    tmp_path: Path,
    test_case: MissingConfigGuidanceTestCase,
) -> None:
    with pytest.raises(ConfigError) as error:
        load_config(tmp_path)

    message: str = str(error.value)
    assert message.startswith(test_case.expected_prefix)
    assert test_case.expected_guidance in message


@pytest.mark.parametrize(
    "test_case",
    [
        MissingConfigGuidanceTestCase(
            description="missing config remains optional during discovery",
            expected_prefix="No strata config found",
            expected_guidance="Run 'strata init' to create one.",
            expected_source=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_missing_source_when_finding_optional_config_then_returns_none(
    tmp_path: Path,
    test_case: MissingConfigGuidanceTestCase,
) -> None:
    source: ConfigSource | None = find_config_source(tmp_path)

    assert source is test_case.expected_source


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidConfigSourceTestCase(
            description="invalid dedicated toml names the parse failure",
            strata_toml='roots = ["src/pkg"\n',
            pyproject_toml=None,
            expected_error_type=ConfigError,
            expected_error_fragment="Could not parse",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_source_when_loading_then_raises_config_error(
    tmp_path: Path,
    test_case: InvalidConfigSourceTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.strata_toml or "")

    with pytest.raises(test_case.expected_error_type) as error:
        load_config(tmp_path)

    assert test_case.expected_error_fragment in str(error.value)
