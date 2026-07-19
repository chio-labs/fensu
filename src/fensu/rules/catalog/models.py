"""Resolved catalogue selection models."""

from __future__ import annotations

from dataclasses import dataclass

from fensu.rules.authoring.models import CustomRuleRegistration, RuleSpec


@dataclass(frozen=True, slots=True)
class RuleSelection:
    """Complete catalogue and its resolved blocking, warning, and ignored sets."""

    catalogue: tuple[RuleSpec, ...]
    blocking: tuple[RuleSpec, ...]
    warnings: tuple[RuleSpec, ...]
    ignored: tuple[RuleSpec, ...]
    custom_registrations: tuple[CustomRuleRegistration, ...] = ()
