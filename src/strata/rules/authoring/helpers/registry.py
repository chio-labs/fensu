"""Per-run registry that authored rules self-append to during import."""

from __future__ import annotations

from strata.rules.spec.models import RuleSpec

_REGISTERED: list[RuleSpec] = []


def register(spec: RuleSpec) -> None:
    """Append a compiled rule spec to the per-run registry."""

    _REGISTERED.append(spec)


def collect_registered() -> tuple[RuleSpec, ...]:
    """Return all registered specs and clear the registry for the next run."""

    collected: tuple[RuleSpec, ...] = tuple(_REGISTERED)
    _REGISTERED.clear()
    return collected
