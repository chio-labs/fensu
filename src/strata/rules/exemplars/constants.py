"""Native core codes and their public custom-rule equivalents."""

from strata.rules.authoring.types import RuleCheck
from strata.rules.exemplars.main.annotations._parameter_annotation import (
    parameter_annotation_equivalent,
)

NATIVE_CUSTOM_RULE_EQUIVALENTS: dict[str, RuleCheck] = {
    "SFA001": parameter_annotation_equivalent,
}
