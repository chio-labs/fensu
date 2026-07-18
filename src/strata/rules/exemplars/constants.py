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
from strata.rules.exemplars.main.hygiene._no_assert_in_runtime import (
    no_assert_in_runtime_equivalent,
)
from strata.rules.exemplars.main.hygiene._no_complex_comprehensions import (
    no_complex_comprehensions_equivalent,
)
from strata.rules.exemplars.main.hygiene._no_import_time_side_effects import (
    no_import_time_side_effects_equivalent,
)
from strata.rules.exemplars.main.hygiene._no_magic_numeric_comparisons import (
    no_magic_numeric_comparisons_equivalent,
)
from strata.rules.exemplars.main.hygiene._no_raw_builtin_raise import (
    no_raw_builtin_raise_equivalent,
)
from strata.rules.exemplars.main.hygiene._no_standalone_comments import (
    no_standalone_comments_equivalent,
)
from strata.rules.exemplars.main.hygiene._no_swallowed_exception_probe import (
    no_swallowed_exception_probe_equivalent,
)
from strata.rules.exemplars.main.hygiene._no_unnamed_string_decisions import (
    no_unnamed_string_decisions_equivalent,
)
from strata.rules.exemplars.main.hygiene._single_line_docstrings import (
    single_line_docstrings_equivalent,
)

NATIVE_CUSTOM_RULE_EQUIVALENTS: dict[str, RuleCheck] = {
    "SFA001": parameter_annotation_equivalent,
    "SFA002": return_annotation_equivalent,
    "SFA101": module_variable_annotation_equivalent,
    "SFA102": class_attribute_annotation_equivalent,
    "SFA103": local_variable_annotation_equivalent,
    "SFH001": single_line_docstrings_equivalent,
    "SFH002": no_standalone_comments_equivalent,
    "SFH003": no_raw_builtin_raise_equivalent,
    "SFH004": no_assert_in_runtime_equivalent,
    "SFH005": no_swallowed_exception_probe_equivalent,
    "SFH006": no_complex_comprehensions_equivalent,
    "SFH007": no_unnamed_string_decisions_equivalent,
    "SFH008": no_magic_numeric_comparisons_equivalent,
    "SFH009": no_import_time_side_effects_equivalent,
}
