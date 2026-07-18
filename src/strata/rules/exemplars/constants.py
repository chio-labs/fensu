"""Native core codes and their public custom-rule equivalents."""

from strata.rules.authoring.types import RuleCheck
from strata.rules.exemplars.main.annotations._class_attribute_annotation import (
    class_attribute_annotation_equivalent,
)
from strata.rules.exemplars.main.annotations._local_variable_annotation import (
    local_variable_annotation_equivalent,
)
from strata.rules.exemplars.main.annotations._module_variable_annotation import (
    module_variable_annotation_equivalent,
)
from strata.rules.exemplars.main.annotations._parameter_annotation import (
    parameter_annotation_equivalent,
)
from strata.rules.exemplars.main.annotations._return_annotation import (
    return_annotation_equivalent,
)

NATIVE_CUSTOM_RULE_EQUIVALENTS: dict[str, RuleCheck] = {
    "SFA001": parameter_annotation_equivalent,
    "SFA002": return_annotation_equivalent,
    "SFA101": module_variable_annotation_equivalent,
    "SFA102": class_attribute_annotation_equivalent,
    "SFA103": local_variable_annotation_equivalent,
}
