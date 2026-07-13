"""Resolved catalogue selection models."""

from __future__ import annotations

from dataclasses import dataclass

from strata.rules.authoring.models import RuleSpec


@dataclass(frozen=True, slots=True)
class RuleSelection:
    """Complete catalogue and its resolved blocking, warning, and ignored sets."""

    catalogue: tuple[RuleSpec, ...]
    blocking: tuple[RuleSpec, ...]
    warnings: tuple[RuleSpec, ...]
    ignored: tuple[RuleSpec, ...]
