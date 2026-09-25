"""Opt-in reachability configuration and cache identity contracts."""

import pytest

from fensu.cache.fingerprints._helpers.fingerprints import config_fingerprint
from fensu.config._helpers.defaults import build_config
from fensu.config._helpers.validate import validate_config
from fensu.config.exceptions import ConfigValidationError
from fensu.config.models import Config
from tests.unit.src.fensu.config._test_types import DeadCodeConfigTestCase, DeadCodeErrorTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        DeadCodeConfigTestCase("missing_enabled", {}, False),
        DeadCodeConfigTestCase("disabled", {"enabled": False}, False),
        DeadCodeConfigTestCase("enabled_without_roots", {"enabled": True}, True),
        DeadCodeConfigTestCase(
            "roots_without_enabled",
            {
                "roots": [
                    {
                        "modules": ["orders.handlers"],
                        "symbols": ["run_*"],
                        "reason": "Runtime handler registry.",
                    }
                ]
            },
            False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_valid_dead_code_when_building_then_respects_opt_in(
    test_case: DeadCodeConfigTestCase,
) -> None:
    config: Config = build_config(
        raw={"roots": ["src/orders"], "select": [], "dead_code": dict(test_case.section)}
    )
    assert config.dead_code.enabled == test_case.expected_enabled
    assert ("FFL106" in config.select) == test_case.expected_enabled
    assert not config.warn


@pytest.mark.parametrize(
    "test_case",
    [
        DeadCodeConfigTestCase("disabled", {"enabled": False}, False),
        DeadCodeConfigTestCase(
            "added_root",
            {
                "enabled": True,
                "roots": [
                    {
                        "modules": ["orders.handlers"],
                        "symbols": ["run_*"],
                        "reason": "Runtime handler registry.",
                    }
                ],
            },
            True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_changed_dead_code_when_fingerprinting_then_invalidates_cache(
    test_case: DeadCodeConfigTestCase,
) -> None:
    first: Config = build_config(raw={"roots": ["src/orders"], "dead_code": {"enabled": True}})
    second: Config = build_config(
        raw={"roots": ["src/orders"], "dead_code": dict(test_case.section)}
    )
    assert (
        config_fingerprint(first) != config_fingerprint(second)
    ) == test_case.expected_fingerprint_changed


@pytest.mark.parametrize(
    "test_case",
    [
        DeadCodeErrorTestCase(
            "unknown_key",
            {"roots": [{"module": "orders.handlers", "symbols": ["*"], "reason": "Registry."}]},
            "Unknown dead_code.roots",
        ),
        DeadCodeErrorTestCase(
            "empty_reason",
            {"roots": [{"modules": ["orders.handlers"], "symbols": ["*"], "reason": " "}]},
            "non-empty string",
        ),
        DeadCodeErrorTestCase(
            "invalid_glob",
            {"roots": [{"modules": ["["], "symbols": ["*"], "reason": "Registry."}]},
            "Invalid",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_dead_code_when_validating_then_rejects(
    test_case: DeadCodeErrorTestCase,
) -> None:
    with pytest.raises(ConfigValidationError, match=test_case.expected_message):
        validate_config(raw={"roots": ["src/orders"], "dead_code": dict(test_case.section)})


if __name__ == "__main__":
    pytest.main([__file__, "-q", "-n", "auto", "--dist", "loadfile"])
