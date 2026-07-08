"""Published entry for draining the per-run rule registry."""

from __future__ import annotations

from strata.rules.authoring.helpers.registry import collect_registered as _collect_registered
from strata.rules.authoring.models import RuleSpec


def collect_registered() -> tuple[RuleSpec, ...]:
    """Return all rules registered this run and clear the registry."""

    return _collect_registered()
