"""Configuration exceptions raised while loading or validating fensu config."""

from __future__ import annotations


class ConfigError(Exception):
    """Base error for invalid or missing fensu configuration."""


class ConfigValidationError(ConfigError):
    """Raised when a config file is present but violates the schema."""
