"""Effective configuration ownership for test-layout rules."""

from __future__ import annotations

from fensu.rules.tests.types import FftCode


def get_test_rule_configuration_inputs(code: FftCode) -> tuple[str, ...]:
    """Return project configuration fields needed to understand one test rule."""

    inputs: dict[FftCode, tuple[str, ...]] = {
        FftCode.TEST_LAYOUT: ("tests", "test_scopes"),
        FftCode.TEST_SCOPE: ("tests", "test_scopes"),
        FftCode.TEST_MIRRORED_ROOT: ("roots", "tooling"),
        FftCode.SRC_MIRROR_DEPTH: ("roots",),
        FftCode.SRC_PACKAGE_EXISTS: ("roots",),
        FftCode.SRC_AREA_EXISTS: ("roots",),
        FftCode.SCRIPTS_MIRROR_DEPTH: ("tooling",),
        FftCode.SCRIPTS_AREA_EXISTS: ("tooling",),
    }
    return inputs.get(code, ())
