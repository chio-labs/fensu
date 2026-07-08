"""Configuration exceptions raised while loading or validating strata config."""

from __future__ import annotations


class ConfigError(Exception):
    """Base error for invalid or missing strata configuration."""


class ConfigValidationError(ConfigError):
    """Raised when a config file is present but violates the schema."""
