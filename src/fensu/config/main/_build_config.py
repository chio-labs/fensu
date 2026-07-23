"""Build validated configuration from an in-memory raw mapping."""

from __future__ import annotations

from collections.abc import Mapping

from fensu.config._helpers.defaults import build_config as build_validated_config
from fensu.config._helpers.validate import validate_config
from fensu.config.exceptions import ConfigValidationError
from fensu.config.models import Config


def build_config(raw: Mapping[str, object]) -> Config:
    """Validate and build configuration from a parsed raw mapping."""

    validate_config(raw)
    raw_options: object = raw.get("rule_options")
    if isinstance(raw_options, Mapping) and raw_options:
        raise ConfigValidationError(
            "Config key rule_options requires the discovered rule catalogue."
        )
    return build_validated_config(raw=raw)
