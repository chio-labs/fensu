"""Errors raised while defining or registering a rule."""

from __future__ import annotations


class RuleDefinitionError(Exception):
    """A rule's metadata envelope or code namespace is invalid at definition time."""
