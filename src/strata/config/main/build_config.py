"""Build validated configuration from an in-memory raw mapping."""

from __future__ import annotations

from collections.abc import Mapping

from strata.config._helpers.defaults import build_config as build_validated_config
from strata.config._helpers.validate import validate_config
from strata.config.models import Config


def build_config(raw: Mapping[str, object]) -> Config:
    """Validate and build configuration from a parsed raw mapping."""

    validate_config(raw)
    return build_validated_config(raw)
