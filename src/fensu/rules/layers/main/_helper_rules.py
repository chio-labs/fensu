"""Layer helper-boundary rule catalogue entries."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Family
from fensu.rules.layers.types import LayerCode


def helper_rules() -> tuple[RuleSpec, ...]:
    """Build helper-boundary layer rules."""

    return (
        RuleSpec(
            code=LayerCode.NO_CROSS_FILE_HELPER_PRIVATE_CLASS,
            family=Family.LAYERS,
            slug="no-cross-file-use-of-helper-private-class",
            message=(
                "helper-private classes are file-local details; move shared classes to classes/"
            ),
            remediation=(
                "If another module needs this class, move it to the owning classes/ package."
            ),
        ),
    )
