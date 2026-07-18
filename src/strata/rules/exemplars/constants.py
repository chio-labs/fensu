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
from strata.rules.exemplars.main.layers._absolute_imports_only import (
    absolute_imports_only_equivalent,
)
from strata.rules.exemplars.main.layers._no_cross_file_helper_private_classes import (
    no_cross_file_helper_private_classes_equivalent,
)
from strata.rules.exemplars.main.layers._no_star_imports import no_star_imports_equivalent
from strata.rules.exemplars.main.naming._iterator_name_must_produce_iterator import (
    iterator_name_must_produce_iterator_equivalent,
)
from strata.rules.exemplars.main.naming._predicate_must_return_bool import (
    predicate_must_return_bool_equivalent,
)
from strata.rules.exemplars.main.naming._validator_must_not_return import (
    validator_must_not_return_equivalent,
)
from strata.rules.exemplars.main.naming._value_name_must_return_value import (
    value_name_must_return_value_equivalent,
)
from strata.rules.exemplars.main.roles._private_definition_ordering import (
    private_definition_ordering_equivalent,
)
from strata.rules.exemplars.main.shape._default_mutation_return import (
    default_mutation_return_equivalent,
)
from strata.rules.exemplars.main.shape._keyword_only_arguments import (
    keyword_only_arguments_equivalent,
)
from strata.rules.exemplars.main.shape._max_arguments import max_arguments_equivalent
from strata.rules.exemplars.main.shape._max_statements_global import (
    max_statements_global_equivalent,
)
from strata.rules.exemplars.main.shape._mutable_result_model import mutable_result_model_equivalent
from strata.rules.exemplars.main.shape._no_complex_comprehensions import (
    no_complex_comprehensions_shape_equivalent,
)
from strata.rules.exemplars.main.shape._no_outer_state_mutation import (
    no_outer_state_mutation_equivalent,
)
from strata.rules.exemplars.main.shape._parameter_mutation_in_phase_helpers import (
    parameter_mutation_in_phase_helpers_equivalent,
)
from strata.rules.exemplars.main.shape._too_many_distinct_calls import (
    too_many_distinct_calls_equivalent,
)
from strata.rules.exemplars.main.shape._too_many_locals import too_many_locals_equivalent
from strata.rules.exemplars.main.shape._too_many_statements import too_many_statements_equivalent
from strata.rules.exemplars.main.tests._absolute_imports import test_absolute_imports_equivalent
from strata.rules.exemplars.main.tests._no_complex_comprehensions import (
    test_no_complex_comprehensions_equivalent,
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
    "SFN001": validator_must_not_return_equivalent,
    "SFN002": predicate_must_return_bool_equivalent,
    "SFN003": value_name_must_return_value_equivalent,
    "SFN004": iterator_name_must_produce_iterator_equivalent,
    "SFS001": too_many_statements_equivalent,
    "SFS002": too_many_distinct_calls_equivalent,
    "SFS003": too_many_locals_equivalent,
    "SFS010": max_arguments_equivalent,
    "SFS011": max_statements_global_equivalent,
    "SFS102": parameter_mutation_in_phase_helpers_equivalent,
    "SFS110": default_mutation_return_equivalent,
    "SFS120": keyword_only_arguments_equivalent,
    "SFS130": no_outer_state_mutation_equivalent,
    "SFS131": no_complex_comprehensions_shape_equivalent,
    "SFS201": mutable_result_model_equivalent,
    "SFL001": absolute_imports_only_equivalent,
    "SFL002": no_star_imports_equivalent,
    "SFL110": no_cross_file_helper_private_classes_equivalent,
    "SFR503": private_definition_ordering_equivalent,
    "SFT102": test_absolute_imports_equivalent,
    "SFT106": test_no_complex_comprehensions_equivalent,
}
