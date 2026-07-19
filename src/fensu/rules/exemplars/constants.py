"""Native core codes and their public custom-rule equivalents."""

from fensu.rules.authoring.types import RuleCheck
from fensu.rules.exemplars._helpers.local_roles import (
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
from fensu.rules.exemplars.main.annotations._class_attribute_annotation import (
    class_attribute_annotation_equivalent,
)
from fensu.rules.exemplars.main.annotations._local_variable_annotation import (
    local_variable_annotation_equivalent,
)
from fensu.rules.exemplars.main.annotations._module_variable_annotation import (
    module_variable_annotation_equivalent,
)
from fensu.rules.exemplars.main.annotations._parameter_annotation import (
    parameter_annotation_equivalent,
)
from fensu.rules.exemplars.main.annotations._return_annotation import (
    return_annotation_equivalent,
)
from fensu.rules.exemplars.main.hygiene._no_assert_in_runtime import (
    no_assert_in_runtime_equivalent,
)
from fensu.rules.exemplars.main.hygiene._no_complex_comprehensions import (
    no_complex_comprehensions_equivalent,
)
from fensu.rules.exemplars.main.hygiene._no_import_time_side_effects import (
    no_import_time_side_effects_equivalent,
)
from fensu.rules.exemplars.main.hygiene._no_magic_numeric_comparisons import (
    no_magic_numeric_comparisons_equivalent,
)
from fensu.rules.exemplars.main.hygiene._no_raw_builtin_raise import (
    no_raw_builtin_raise_equivalent,
)
from fensu.rules.exemplars.main.hygiene._no_standalone_comments import (
    no_standalone_comments_equivalent,
)
from fensu.rules.exemplars.main.hygiene._no_swallowed_exception_probe import (
    no_swallowed_exception_probe_equivalent,
)
from fensu.rules.exemplars.main.hygiene._no_unnamed_string_decisions import (
    no_unnamed_string_decisions_equivalent,
)
from fensu.rules.exemplars.main.hygiene._single_line_docstrings import (
    single_line_docstrings_equivalent,
)
from fensu.rules.exemplars.main.layers._absolute_imports_only import (
    absolute_imports_only_equivalent,
)
from fensu.rules.exemplars.main.layers._no_cross_domain_private_main_imports import (
    no_cross_domain_private_main_imports_equivalent,
)
from fensu.rules.exemplars.main.layers._no_cross_file_helper_private_classes import (
    no_cross_file_helper_private_classes_equivalent,
)
from fensu.rules.exemplars.main.layers._no_cross_package_internals import (
    no_cross_package_internals_equivalent,
)
from fensu.rules.exemplars.main.layers._no_internal_public_surface_imports import (
    no_internal_public_surface_imports_equivalent,
)
from fensu.rules.exemplars.main.layers._no_runtime_imports_from_tooling import (
    no_runtime_imports_from_tooling_equivalent,
)
from fensu.rules.exemplars.main.layers._no_sibling_package_internals import (
    no_sibling_package_internals_equivalent,
)
from fensu.rules.exemplars.main.layers._no_star_imports import no_star_imports_equivalent
from fensu.rules.exemplars.main.layers._public_main_entry_external_use import (
    public_main_entry_external_use_equivalent,
)
from fensu.rules.exemplars.main.naming._iterator_name_must_produce_iterator import (
    iterator_name_must_produce_iterator_equivalent,
)
from fensu.rules.exemplars.main.naming._predicate_must_return_bool import (
    predicate_must_return_bool_equivalent,
)
from fensu.rules.exemplars.main.naming._validator_must_not_return import (
    validator_must_not_return_equivalent,
)
from fensu.rules.exemplars.main.naming._value_name_must_return_value import (
    value_name_must_return_value_equivalent,
)
from fensu.rules.exemplars.main.roles._banned_generic_package_name import (
    banned_generic_package_name_equivalent,
)
from fensu.rules.exemplars.main.roles._custom_rule_test_coverage import (
    custom_rule_test_coverage_equivalent,
)
from fensu.rules.exemplars.main.roles._helpers_package_layout import (
    helpers_package_layout_equivalent,
)
from fensu.rules.exemplars.main.roles._leaf_main_boundary import leaf_main_boundary_equivalent
from fensu.rules.exemplars.main.roles._main_entry_name_collision import (
    main_entry_name_collision_equivalent,
)
from fensu.rules.exemplars.main.roles._main_package_layout import main_package_layout_equivalent
from fensu.rules.exemplars.main.roles._private_definition_ordering import (
    private_definition_ordering_equivalent,
)
from fensu.rules.exemplars.main.roles._shared_domain_prefix import shared_domain_prefix_equivalent
from fensu.rules.exemplars.main.roles._tooling_package_layout import (
    tooling_package_layout_equivalent,
)
from fensu.rules.exemplars.main.roles._top_level_domain_shape import (
    top_level_domain_shape_equivalent,
)
from fensu.rules.exemplars.main.shape._default_mutation_return import (
    default_mutation_return_equivalent,
)
from fensu.rules.exemplars.main.shape._keyword_only_arguments import (
    keyword_only_arguments_equivalent,
)
from fensu.rules.exemplars.main.shape._max_arguments import max_arguments_equivalent
from fensu.rules.exemplars.main.shape._max_statements_global import (
    max_statements_global_equivalent,
)
from fensu.rules.exemplars.main.shape._meaningful_project_result_discarded import (
    meaningful_project_result_discarded_equivalent,
)
from fensu.rules.exemplars.main.shape._mutable_result_model import mutable_result_model_equivalent
from fensu.rules.exemplars.main.shape._no_complex_comprehensions import (
    no_complex_comprehensions_shape_equivalent,
)
from fensu.rules.exemplars.main.shape._no_outer_state_mutation import (
    no_outer_state_mutation_equivalent,
)
from fensu.rules.exemplars.main.shape._parameter_mutation_in_phase_helpers import (
    parameter_mutation_in_phase_helpers_equivalent,
)
from fensu.rules.exemplars.main.shape._too_many_distinct_calls import (
    too_many_distinct_calls_equivalent,
)
from fensu.rules.exemplars.main.shape._too_many_locals import too_many_locals_equivalent
from fensu.rules.exemplars.main.shape._too_many_statements import too_many_statements_equivalent
from fensu.rules.exemplars.main.tests._absolute_imports import test_absolute_imports_equivalent
from fensu.rules.exemplars.main.tests._conditional_and_filename import (
    _test_file_name_equivalent,
    test_no_if_in_tests_equivalent,
)
from fensu.rules.exemplars.main.tests._function_basics import (
    _accepts_test_case_equivalent,
    _dataclass_parametrize_equivalent,
    test_function_name_equivalent,
)
from fensu.rules.exemplars.main.tests._function_expectations import (
    _parametrize_arguments_equivalent,
    _parametrize_test_case_equivalent,
    expected_field_assertion_equivalent,
)
from fensu.rules.exemplars.main.tests._layout_roots import (
    _test_scope_equivalent,
    test_layout_equivalent,
)
from fensu.rules.exemplars.main.tests._layout_runtime import (
    _src_package_exists_equivalent,
    src_mirror_depth_equivalent,
)
from fensu.rules.exemplars.main.tests._layout_tooling import (
    _scripts_area_exists_equivalent,
    scripts_mirror_depth_equivalent,
)
from fensu.rules.exemplars.main.tests._local_test_case_types import (
    _local_test_case_constructors_equivalent,
    test_case_annotation_equivalent,
)
from fensu.rules.exemplars.main.tests._local_test_types_file import (
    local_test_types_file_equivalent,
)
from fensu.rules.exemplars.main.tests._module_style import (
    _test_no_top_level_helpers_equivalent,
    _test_private_constant_order_equivalent,
    test_init_module_empty_equivalent,
)
from fensu.rules.exemplars.main.tests._no_complex_comprehensions import (
    test_no_complex_comprehensions_equivalent,
)
from fensu.rules.exemplars.main.tests._parametrize_cases import (
    _description_lambda_ids_equivalent,
    no_dict_test_cases_equivalent,
)
from fensu.rules.exemplars.main.tests._parametrize_shape import (
    _inline_parametrize_values_equivalent,
    _nonempty_parametrize_values_equivalent,
    parametrize_ids_equivalent,
)
from fensu.rules.exemplars.main.tests._src_area_exists import src_area_exists_equivalent
from fensu.rules.exemplars.main.tests._test_mirrored_root import test_mirrored_root_equivalent
from fensu.rules.exemplars.main.tests._test_types import (
    _local_test_types_import_equivalent,
    _test_types_expected_field_equivalent,
    test_types_description_equivalent,
)

NATIVE_CUSTOM_RULE_EQUIVALENTS: dict[str, RuleCheck] = {
    "FFA001": parameter_annotation_equivalent,
    "FFA002": return_annotation_equivalent,
    "FFA101": module_variable_annotation_equivalent,
    "FFA102": class_attribute_annotation_equivalent,
    "FFA103": local_variable_annotation_equivalent,
    "FFH001": single_line_docstrings_equivalent,
    "FFH002": no_standalone_comments_equivalent,
    "FFH003": no_raw_builtin_raise_equivalent,
    "FFH004": no_assert_in_runtime_equivalent,
    "FFH005": no_swallowed_exception_probe_equivalent,
    "FFH006": no_complex_comprehensions_equivalent,
    "FFH007": no_unnamed_string_decisions_equivalent,
    "FFH008": no_magic_numeric_comparisons_equivalent,
    "FFH009": no_import_time_side_effects_equivalent,
    "FFN001": validator_must_not_return_equivalent,
    "FFN002": predicate_must_return_bool_equivalent,
    "FFN003": value_name_must_return_value_equivalent,
    "FFN004": iterator_name_must_produce_iterator_equivalent,
    "FFS001": too_many_statements_equivalent,
    "FFS002": too_many_distinct_calls_equivalent,
    "FFS003": too_many_locals_equivalent,
    "FFS010": max_arguments_equivalent,
    "FFS011": max_statements_global_equivalent,
    "FFS101": meaningful_project_result_discarded_equivalent,
    "FFS102": parameter_mutation_in_phase_helpers_equivalent,
    "FFS110": default_mutation_return_equivalent,
    "FFS120": keyword_only_arguments_equivalent,
    "FFS130": no_outer_state_mutation_equivalent,
    "FFS131": no_complex_comprehensions_shape_equivalent,
    "FFS201": mutable_result_model_equivalent,
    "FFL001": absolute_imports_only_equivalent,
    "FFL002": no_star_imports_equivalent,
    "FFL101": no_sibling_package_internals_equivalent,
    "FFL102": no_cross_package_internals_equivalent,
    "FFL103": no_internal_public_surface_imports_equivalent,
    "FFL104": no_cross_domain_private_main_imports_equivalent,
    "FFL105": public_main_entry_external_use_equivalent,
    "FFL110": no_cross_file_helper_private_classes_equivalent,
    "FFL301": no_runtime_imports_from_tooling_equivalent,
    "FFR001": models_only_models_equivalent,
    "FFR002": types_only_types_equivalent,
    "FFR003": constants_only_constants_equivalent,
    "FFR004": exceptions_only_exceptions_equivalent,
    "FFR101": model_declaration_outside_models_equivalent,
    "FFR102": type_declaration_outside_types_equivalent,
    "FFR103": constant_outside_constants_equivalent,
    "FFR104": exception_declaration_outside_exceptions_equivalent,
    "FFR201": banned_generic_filename_equivalent,
    "FFR202": helpers_module_name_equivalent,
    "FFR203": classes_module_name_equivalent,
    "FFR204": banned_generic_package_name_equivalent,
    "FFR205": helpers_classes_file_private_equivalent,
    "FFR301": helpers_package_layout_equivalent,
    "FFR302": main_package_layout_equivalent,
    "FFR303": helpers_reserved_role_filenames_equivalent,
    "FFR304": nested_direct_modules_equivalent,
    "FFR305": nested_direct_subpackages_equivalent,
    "FFR306": top_level_domain_shape_equivalent,
    "FFR307": top_level_direct_modules_equivalent,
    "FFR308": shared_domain_prefix_equivalent,
    "FFR309": leaf_main_boundary_equivalent,
    "FFR401": entry_module_shape_equivalent,
    "FFR402": init_module_empty_equivalent,
    "FFR403": no_reexport_shim_equivalent,
    "FFR404": no_internal_helper_exports_equivalent,
    "FFR405": main_entry_name_collision_equivalent,
    "FFR406": public_surface_shape_equivalent,
    "FFR501": classes_one_class_per_module_equivalent,
    "FFR502": helpers_package_shape_equivalent,
    "FFR503": private_definition_ordering_equivalent,
    "FFR601": source_file_line_count_equivalent,
    "FFR701": tooling_entrypoint_shape_equivalent,
    "FFR702": tooling_entrypoint_delegation_equivalent,
    "FFR703": tooling_entrypoint_line_count_equivalent,
    "FFR704": rules_role_content_equivalent,
    "FFR705": tooling_package_layout_equivalent,
    "FFR706": descriptive_rule_module_names_equivalent,
    "FFR707": custom_rule_test_coverage_equivalent,
    "FFT001": test_layout_equivalent,
    "FFT002": _test_scope_equivalent,
    "FFT003": test_mirrored_root_equivalent,
    "FFT004": src_mirror_depth_equivalent,
    "FFT005": _src_package_exists_equivalent,
    "FFT006": src_area_exists_equivalent,
    "FFT007": scripts_mirror_depth_equivalent,
    "FFT008": _scripts_area_exists_equivalent,
    "FFT101": test_init_module_empty_equivalent,
    "FFT102": test_absolute_imports_equivalent,
    "FFT103": _test_no_top_level_helpers_equivalent,
    "FFT104": test_no_if_in_tests_equivalent,
    "FFT105": _test_private_constant_order_equivalent,
    "FFT106": test_no_complex_comprehensions_equivalent,
    "FFT201": test_types_description_equivalent,
    "FFT202": _test_types_expected_field_equivalent,
    "FFT203": _local_test_types_import_equivalent,
    "FFT204": local_test_types_file_equivalent,
    "FFT301": _test_file_name_equivalent,
    "FFT302": test_function_name_equivalent,
    "FFT401": _dataclass_parametrize_equivalent,
    "FFT402": _accepts_test_case_equivalent,
    "FFT403": test_case_annotation_equivalent,
    "FFT404": expected_field_assertion_equivalent,
    "FFT405": _parametrize_arguments_equivalent,
    "FFT406": _parametrize_test_case_equivalent,
    "FFT407": parametrize_ids_equivalent,
    "FFT408": _inline_parametrize_values_equivalent,
    "FFT411": _nonempty_parametrize_values_equivalent,
    "FFT412": no_dict_test_cases_equivalent,
    "FFT413": _local_test_case_constructors_equivalent,
    "FFT414": _description_lambda_ids_equivalent,
}
