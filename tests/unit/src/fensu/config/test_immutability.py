"""Tests for Config immutability."""

from __future__ import annotations

import operator
from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import cast

import pytest

from fensu.config.main.load_config import load_config
from fensu.config.models import Config
from fensu.rules.authoring.types import Threshold
from tests.unit.src.fensu.config._test_types import ConfigImmutabilityTestCase
from tests.unit.src.fensu.config.helpers import write_fensu_toml


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigImmutabilityTestCase(
            description="config dataclass fields cannot be reassigned",
            config_text='roots = ["src/pkg"]\n',
            expected_error_type=FrozenInstanceError,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_loaded_config_when_reassigning_field_then_raises_frozen_instance_error(
    tmp_path: Path,
    test_case: ConfigImmutabilityTestCase,
) -> None:
    write_fensu_toml(root=tmp_path, contents=test_case.config_text)
    config: Config = load_config(tmp_path)

    with pytest.raises(test_case.expected_error_type):
        Config.__setattr__(config, "roots", ("src/other",))


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigImmutabilityTestCase(
            description="threshold mapping cannot be mutated",
            config_text='roots = ["src/pkg"]\n',
            expected_error_type=TypeError,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_loaded_config_when_mutating_thresholds_then_raises_type_error(
    tmp_path: Path,
    test_case: ConfigImmutabilityTestCase,
) -> None:
    write_fensu_toml(root=tmp_path, contents=test_case.config_text)
    config: Config = load_config(tmp_path)
    mutable_thresholds: MutableMapping[Threshold, int] = cast(
        "MutableMapping[Threshold, int]", config.thresholds
    )

    with pytest.raises(test_case.expected_error_type):
        operator.setitem(mutable_thresholds, Threshold.MAX_STATEMENTS, 1)


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigImmutabilityTestCase(
            description="role threshold mapping cannot be mutated",
            config_text='roots = ["src/pkg"]\n[roles.entry]\nmax_statements = 30\n',
            expected_error_type=TypeError,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_loaded_config_when_mutating_role_thresholds_then_raises_type_error(
    tmp_path: Path,
    test_case: ConfigImmutabilityTestCase,
) -> None:
    write_fensu_toml(root=tmp_path, contents=test_case.config_text)
    config: Config = load_config(tmp_path)
    mutable_role_thresholds: MutableMapping[Threshold, int] = cast(
        "MutableMapping[Threshold, int]", config.role_thresholds["entry"]
    )

    with pytest.raises(test_case.expected_error_type):
        operator.setitem(mutable_role_thresholds, Threshold.MAX_STATEMENTS, 1)
