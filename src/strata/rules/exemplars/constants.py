"""Native core codes and their public custom-rule equivalents."""

from strata.rules.authoring.types import RuleCheck
from strata.rules.exemplars._helpers.local_roles import (
    banned_generic_filename_equivalent,
    classes_module_name_equivalent,
    classes_one_class_per_module_equivalent,
    constant_outside_constants_equivalent,
    constants_only_constants_equivalent,
    descriptive_rule_module_names_equivalent,
    entry_module_shape_equivalent,
    exception_declaration_outside_exceptions_equivalent,
    exceptions_only_exceptions_equivalent,
    helpers_classes_file_private_equivalent,
    helpers_module_name_equivalent,
    helpers_package_shape_equivalent,
    helpers_reserved_role_filenames_equivalent,
    init_module_empty_equivalent,
    model_declaration_outside_models_equivalent,
    models_only_models_equivalent,
    nested_direct_modules_equivalent,
    nested_direct_subpackages_equivalent,
    no_internal_helper_exports_equivalent,
    no_reexport_shim_equivalent,
    public_surface_shape_equivalent,
    rules_role_content_equivalent,
    source_file_line_count_equivalent,
    tooling_entrypoint_delegation_equivalent,
    tooling_entrypoint_line_count_equivalent,
    tooling_entrypoint_shape_equivalent,
    top_level_direct_modules_equivalent,
    type_declaration_outside_types_equivalent,
    types_only_types_equivalent,
)
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
from strata.rules.exemplars.main.layers._no_cross_domain_private_main_imports import (
    no_cross_domain_private_main_imports_equivalent,
)
from strata.rules.exemplars.main.layers._no_cross_file_helper_private_classes import (
    no_cross_file_helper_private_classes_equivalent,
)
from strata.rules.exemplars.main.layers._no_cross_package_internals import (
    no_cross_package_internals_equivalent,
)
from strata.rules.exemplars.main.layers._no_internal_public_surface_imports import (
    no_internal_public_surface_imports_equivalent,
)
from strata.rules.exemplars.main.layers._no_runtime_imports_from_tooling import (
    no_runtime_imports_from_tooling_equivalent,
)
from strata.rules.exemplars.main.layers._no_sibling_package_internals import (
    no_sibling_package_internals_equivalent,
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
from strata.rules.exemplars.main.roles._banned_generic_package_name import (
    banned_generic_package_name_equivalent,
)
from strata.rules.exemplars.main.roles._custom_rule_test_coverage import (
    custom_rule_test_coverage_equivalent,
)
from strata.rules.exemplars.main.roles._main_entry_name_collision import (
    main_entry_name_collision_equivalent,
)
from strata.rules.exemplars.main.roles._private_definition_ordering import (
    private_definition_ordering_equivalent,
)
from strata.rules.exemplars.main.roles._tooling_package_layout import (
    tooling_package_layout_equivalent,
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
from strata.rules.exemplars.main.shape._meaningful_project_result_discarded import (
    meaningful_project_result_discarded_equivalent,
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
from strata.rules.exemplars.main.tests._conditional_and_filename import (
    _test_file_name_equivalent,
    test_no_if_in_tests_equivalent,
)
from strata.rules.exemplars.main.tests._function_basics import (
    _accepts_test_case_equivalent,
    _dataclass_parametrize_equivalent,
    test_function_name_equivalent,
)
from strata.rules.exemplars.main.tests._function_expectations import (
    _parametrize_arguments_equivalent,
    _parametrize_test_case_equivalent,
    expected_field_assertion_equivalent,
)
from strata.rules.exemplars.main.tests._layout_roots import (
    _test_scope_equivalent,
    test_layout_equivalent,
)
from strata.rules.exemplars.main.tests._layout_runtime import (
    _src_package_exists_equivalent,
    src_mirror_depth_equivalent,
)
from strata.rules.exemplars.main.tests._layout_tooling import (
    _scripts_area_exists_equivalent,
    scripts_mirror_depth_equivalent,
)
from strata.rules.exemplars.main.tests._local_test_case_types import (
    _local_test_case_constructors_equivalent,
    test_case_annotation_equivalent,
)
from strata.rules.exemplars.main.tests._local_test_types_file import (
    local_test_types_file_equivalent,
)
from strata.rules.exemplars.main.tests._module_style import (
    _test_no_top_level_helpers_equivalent,
    _test_private_constant_order_equivalent,
    test_init_module_empty_equivalent,
)
from strata.rules.exemplars.main.tests._no_complex_comprehensions import (
    test_no_complex_comprehensions_equivalent,
)
from strata.rules.exemplars.main.tests._parametrize_cases import (
    _description_lambda_ids_equivalent,
    no_dict_test_cases_equivalent,
)
from strata.rules.exemplars.main.tests._parametrize_shape import (
    _inline_parametrize_values_equivalent,
    _nonempty_parametrize_values_equivalent,
    parametrize_ids_equivalent,
)
from strata.rules.exemplars.main.tests._src_area_exists import src_area_exists_equivalent
from strata.rules.exemplars.main.tests._test_mirrored_root import test_mirrored_root_equivalent
from strata.rules.exemplars.main.tests._test_types import (
    _local_test_types_import_equivalent,
    _test_types_expected_field_equivalent,
    test_types_description_equivalent,
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
    "SFS101": meaningful_project_result_discarded_equivalent,
    "SFS102": parameter_mutation_in_phase_helpers_equivalent,
    "SFS110": default_mutation_return_equivalent,
    "SFS120": keyword_only_arguments_equivalent,
    "SFS130": no_outer_state_mutation_equivalent,
    "SFS131": no_complex_comprehensions_shape_equivalent,
    "SFS201": mutable_result_model_equivalent,
    "SFL001": absolute_imports_only_equivalent,
    "SFL002": no_star_imports_equivalent,
    "SFL101": no_sibling_package_internals_equivalent,
    "SFL102": no_cross_package_internals_equivalent,
    "SFL103": no_internal_public_surface_imports_equivalent,
    "SFL104": no_cross_domain_private_main_imports_equivalent,
    "SFL110": no_cross_file_helper_private_classes_equivalent,
    "SFL301": no_runtime_imports_from_tooling_equivalent,
    "SFR001": models_only_models_equivalent,
    "SFR002": types_only_types_equivalent,
    "SFR003": constants_only_constants_equivalent,
    "SFR004": exceptions_only_exceptions_equivalent,
    "SFR101": model_declaration_outside_models_equivalent,
    "SFR102": type_declaration_outside_types_equivalent,
    "SFR103": constant_outside_constants_equivalent,
    "SFR104": exception_declaration_outside_exceptions_equivalent,
    "SFR201": banned_generic_filename_equivalent,
    "SFR202": helpers_module_name_equivalent,
    "SFR203": classes_module_name_equivalent,
    "SFR204": banned_generic_package_name_equivalent,
    "SFR205": helpers_classes_file_private_equivalent,
    "SFR303": helpers_reserved_role_filenames_equivalent,
    "SFR304": nested_direct_modules_equivalent,
    "SFR305": nested_direct_subpackages_equivalent,
    "SFR307": top_level_direct_modules_equivalent,
    "SFR401": entry_module_shape_equivalent,
    "SFR402": init_module_empty_equivalent,
    "SFR403": no_reexport_shim_equivalent,
    "SFR404": no_internal_helper_exports_equivalent,
    "SFR405": main_entry_name_collision_equivalent,
    "SFR406": public_surface_shape_equivalent,
    "SFR501": classes_one_class_per_module_equivalent,
    "SFR502": helpers_package_shape_equivalent,
    "SFR503": private_definition_ordering_equivalent,
    "SFR601": source_file_line_count_equivalent,
    "SFR701": tooling_entrypoint_shape_equivalent,
    "SFR702": tooling_entrypoint_delegation_equivalent,
    "SFR703": tooling_entrypoint_line_count_equivalent,
    "SFR704": rules_role_content_equivalent,
    "SFR705": tooling_package_layout_equivalent,
    "SFR706": descriptive_rule_module_names_equivalent,
    "SFR707": custom_rule_test_coverage_equivalent,
    "SFT001": test_layout_equivalent,
    "SFT002": _test_scope_equivalent,
    "SFT003": test_mirrored_root_equivalent,
    "SFT004": src_mirror_depth_equivalent,
    "SFT005": _src_package_exists_equivalent,
    "SFT006": src_area_exists_equivalent,
    "SFT007": scripts_mirror_depth_equivalent,
    "SFT008": _scripts_area_exists_equivalent,
    "SFT101": test_init_module_empty_equivalent,
    "SFT102": test_absolute_imports_equivalent,
    "SFT103": _test_no_top_level_helpers_equivalent,
    "SFT104": test_no_if_in_tests_equivalent,
    "SFT105": _test_private_constant_order_equivalent,
    "SFT106": test_no_complex_comprehensions_equivalent,
    "SFT201": test_types_description_equivalent,
    "SFT202": _test_types_expected_field_equivalent,
    "SFT203": _local_test_types_import_equivalent,
    "SFT204": local_test_types_file_equivalent,
    "SFT301": _test_file_name_equivalent,
    "SFT302": test_function_name_equivalent,
    "SFT401": _dataclass_parametrize_equivalent,
    "SFT402": _accepts_test_case_equivalent,
    "SFT403": test_case_annotation_equivalent,
    "SFT404": expected_field_assertion_equivalent,
    "SFT405": _parametrize_arguments_equivalent,
    "SFT406": _parametrize_test_case_equivalent,
    "SFT407": parametrize_ids_equivalent,
    "SFT408": _inline_parametrize_values_equivalent,
    "SFT411": _nonempty_parametrize_values_equivalent,
    "SFT412": no_dict_test_cases_equivalent,
    "SFT413": _local_test_case_constructors_equivalent,
    "SFT414": _description_lambda_ids_equivalent,
}
