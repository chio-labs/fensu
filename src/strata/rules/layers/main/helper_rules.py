"""Layer helper-boundary rule catalogue entries."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family
from strata.rules.layers.helpers.checks import no_cross_file_helper_private_classes
from strata.rules.layers.types import LayerCode


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
            check=no_cross_file_helper_private_classes,
        ),
    )
