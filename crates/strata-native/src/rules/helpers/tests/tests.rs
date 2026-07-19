//! Tests-family policy over shared per-file fact rows.

use strata_facts::extension::models::ProgramHandle;
use strata_facts::facts::models::{ParametrizeRow, TestFunctionRow};

use crate::rules::constants::{
    TEST_ABSOLUTE_IMPORTS_CODE, TEST_ACCEPTS_TEST_CASE_CODE, TEST_CASE_ANNOTATION_CODE,
    TEST_DATACLASS_PARAMETRIZE_CODE, TEST_DESCRIPTION_FIELD_NAME, TEST_DESCRIPTION_LAMBDA_IDS_CODE,
    TEST_EXPECTED_FIELD_ASSERTION_CODE, TEST_EXPECTED_FIELD_PREFIX, TEST_FILE_NAME_CODE,
    TEST_FUNCTION_NAME_CODE, TEST_INIT_MODULE_EMPTY_CODE, TEST_INIT_MODULE_NAME,
    TEST_INLINE_PARAMETRIZE_VALUES_CODE, TEST_LAYOUT_CODE, TEST_LOCAL_TEST_CASE_CONSTRUCTORS_CODE,
    TEST_LOCAL_TEST_TYPES_FILE_CODE, TEST_LOCAL_TEST_TYPES_IMPORT_CODE,
    TEST_MINIMUM_PARAMETRIZE_ARGUMENTS, TEST_MIRRORED_ROOT_CODE,
    TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE, TEST_NO_COMPLEX_COMPREHENSIONS_CODE,
    TEST_NO_DICT_TEST_CASES_CODE, TEST_NO_IF_IN_TESTS_CODE, TEST_NO_TOP_LEVEL_HELPERS_CODE,
    TEST_PARAMETRIZE_ARGUMENTS_CODE, TEST_PARAMETRIZE_IDS_CODE, TEST_PARAMETRIZE_TEST_CASE_CODE,
    TEST_PRIVATE_CONSTANT_ORDER_CODE, TEST_SCOPE_CODE, TEST_SCRIPTS_AREA_EXISTS_CODE,
    TEST_SCRIPTS_MIRROR_DEPTH_CODE, TEST_SRC_AREA_EXISTS_CODE, TEST_SRC_MIRROR_DEPTH_CODE,
    TEST_SRC_PACKAGE_EXISTS_CODE, TEST_TYPES_DESCRIPTION_CODE, TEST_TYPES_EXPECTED_FIELD_CODE,
};
use crate::rules::helpers::test_layout::{is_layout_code, layout_faults};
use crate::rules::helpers::test_names::{description_ids_fault, valid_test_name};
use crate::rules::models::{NativeFaultRow, NativeProjectQuery, NativeRuleContext};

const TEST_SCOPE: &str = "test";
const TEST_CASE_NAME: &str = "test_case";
const TEST_TYPES_FILE: &str = "_test_types.py";
const SCENARIO_MODELS_FILE: &str = "scenario_models.py";
const HELPER_MODULES: &[&str] = &["_test_helpers.py", "helpers.py"];
const NON_TEST_MODULES: &[&str] = &[
    "_test_helpers.py",
    TEST_TYPES_FILE,
    "helpers.py",
    "conftest.py",
    "__init__.py",
];

pub(crate) fn test_faults(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Option<Vec<NativeFaultRow>> {
    if !is_test_code(code) {
        return None;
    }
    if context.scope != TEST_SCOPE {
        return Some(Vec::new());
    }
    let file_name = context
        .repository_path
        .rsplit('/')
        .next()
        .unwrap_or_default();
    let test_module = !NON_TEST_MODULES.contains(&file_name);
    if file_name == SCENARIO_MODELS_FILE && code == TEST_LAYOUT_CODE {
        return Some(location_faults(
            code,
            &program.test_module_rows().scenario_invalid,
        ));
    }
    if is_layout_code(code) {
        return Some(layout_faults(code, context, file_name));
    }
    let faults = match code {
        TEST_INIT_MODULE_EMPTY_CODE => init_module_faults(program, code, file_name),
        TEST_ABSOLUTE_IMPORTS_CODE => program
            .reference_rows()
            .imports
            .iter()
            .filter(|row| row.from_import && row.relative_level > 0)
            .map(|row| location_fault(code, row.line, row.column))
            .collect(),
        TEST_NO_TOP_LEVEL_HELPERS_CODE if test_module => {
            location_faults(code, &program.test_module_rows().top_level_helpers)
        }
        TEST_NO_IF_IN_TESTS_CODE if HELPER_MODULES.contains(&file_name) => location_faults(
            code,
            &program.control_flow_rows().top_level_test_conditionals,
        ),
        TEST_NO_IF_IN_TESTS_CODE if test_module => program
            .test_function_rows()
            .iter()
            .flat_map(|row| location_faults(code, &row.conditional_locations))
            .collect(),
        TEST_PRIVATE_CONSTANT_ORDER_CODE if test_module => {
            location_faults(code, &program.test_module_rows().private_after_test)
        }
        TEST_NO_COMPLEX_COMPREHENSIONS_CODE => {
            location_faults(code, &program.control_flow_rows().complex_comprehensions)
        }
        TEST_TYPES_DESCRIPTION_CODE if file_name == TEST_TYPES_FILE => program
            .dataclass_rows()
            .iter()
            .filter(|row| {
                !row.field_names
                    .iter()
                    .any(|name| name == TEST_DESCRIPTION_FIELD_NAME)
            })
            .map(|row| location_fault(code, row.line, row.column))
            .collect(),
        TEST_TYPES_EXPECTED_FIELD_CODE if file_name == TEST_TYPES_FILE => program
            .dataclass_rows()
            .iter()
            .filter(|row| {
                !row.field_names
                    .iter()
                    .any(|name| name.starts_with(TEST_EXPECTED_FIELD_PREFIX))
            })
            .map(|row| location_fault(code, row.line, row.column))
            .collect(),
        TEST_LOCAL_TEST_TYPES_IMPORT_CODE if test_module => {
            local_test_types_import_faults(program, code, &context.repository_path)
        }
        TEST_LOCAL_TEST_TYPES_FILE_CODE if test_module => {
            let path = sibling_path(&context.repository_path, TEST_TYPES_FILE);
            if observed_bool(context, "is_file", &path) {
                Vec::new()
            } else {
                vec![path_fault(code, None)]
            }
        }
        TEST_FILE_NAME_CODE if test_module && !file_name.starts_with("test_") => {
            vec![path_fault(code, None)]
        }
        code if is_test_function_code(code) && test_module => {
            let local_types = local_test_case_types(program, context);
            program
                .test_function_rows()
                .iter()
                .flat_map(|row| test_function_faults(code, row, &local_types))
                .collect()
        }
        _ => Vec::new(),
    };
    Some(faults)
}

fn is_test_code(code: &str) -> bool {
    matches!(
        code,
        TEST_LAYOUT_CODE
            | TEST_SCOPE_CODE
            | TEST_MIRRORED_ROOT_CODE
            | TEST_SRC_MIRROR_DEPTH_CODE
            | TEST_SRC_PACKAGE_EXISTS_CODE
            | TEST_SRC_AREA_EXISTS_CODE
            | TEST_SCRIPTS_MIRROR_DEPTH_CODE
            | TEST_SCRIPTS_AREA_EXISTS_CODE
            | TEST_INIT_MODULE_EMPTY_CODE
            | TEST_ABSOLUTE_IMPORTS_CODE
            | TEST_NO_TOP_LEVEL_HELPERS_CODE
            | TEST_NO_IF_IN_TESTS_CODE
            | TEST_PRIVATE_CONSTANT_ORDER_CODE
            | TEST_NO_COMPLEX_COMPREHENSIONS_CODE
            | TEST_TYPES_DESCRIPTION_CODE
            | TEST_TYPES_EXPECTED_FIELD_CODE
            | TEST_LOCAL_TEST_TYPES_IMPORT_CODE
            | TEST_LOCAL_TEST_TYPES_FILE_CODE
            | TEST_FILE_NAME_CODE
            | TEST_FUNCTION_NAME_CODE
            | TEST_DATACLASS_PARAMETRIZE_CODE
            | TEST_ACCEPTS_TEST_CASE_CODE
            | TEST_CASE_ANNOTATION_CODE
            | TEST_EXPECTED_FIELD_ASSERTION_CODE
            | TEST_PARAMETRIZE_ARGUMENTS_CODE
            | TEST_PARAMETRIZE_TEST_CASE_CODE
            | TEST_PARAMETRIZE_IDS_CODE
            | TEST_INLINE_PARAMETRIZE_VALUES_CODE
            | TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE
            | TEST_NO_DICT_TEST_CASES_CODE
            | TEST_LOCAL_TEST_CASE_CONSTRUCTORS_CODE
            | TEST_DESCRIPTION_LAMBDA_IDS_CODE
    )
}

fn is_test_function_code(code: &str) -> bool {
    matches!(
        code,
        TEST_FUNCTION_NAME_CODE
            | TEST_DATACLASS_PARAMETRIZE_CODE
            | TEST_ACCEPTS_TEST_CASE_CODE
            | TEST_CASE_ANNOTATION_CODE
            | TEST_EXPECTED_FIELD_ASSERTION_CODE
            | TEST_PARAMETRIZE_ARGUMENTS_CODE
            | TEST_PARAMETRIZE_TEST_CASE_CODE
            | TEST_PARAMETRIZE_IDS_CODE
            | TEST_INLINE_PARAMETRIZE_VALUES_CODE
            | TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE
            | TEST_NO_DICT_TEST_CASES_CODE
            | TEST_LOCAL_TEST_CASE_CONSTRUCTORS_CODE
            | TEST_DESCRIPTION_LAMBDA_IDS_CODE
    )
}

fn init_module_faults(program: &ProgramHandle, code: &str, file_name: &str) -> Vec<NativeFaultRow> {
    if file_name != TEST_INIT_MODULE_NAME || program.test_module_rows().empty_or_docstring_only {
        return Vec::new();
    }
    vec![path_fault(
        code,
        Some("__init__.py must be empty or docstring-only"),
    )]
}

fn local_test_types_import_faults(
    program: &ProgramHandle,
    code: &str,
    repository_path: &str,
) -> Vec<NativeFaultRow> {
    let parent = repository_path
        .rsplit_once('/')
        .map_or("", |(path, _)| path);
    let expected_module = format!("{}._test_types", parent.replace('/', "."));
    program
        .reference_rows()
        .imports
        .iter()
        .filter(|row| {
            let module_name = row.module_parts.join(".");
            row.top_level
                && row.from_import
                && module_name.ends_with("._test_types")
                && module_name != expected_module
        })
        .map(|row| location_fault(code, row.line, row.column))
        .collect()
}

fn test_function_faults(
    code: &str,
    row: &TestFunctionRow,
    local_types: &std::collections::HashSet<String>,
) -> Vec<NativeFaultRow> {
    if code == TEST_FUNCTION_NAME_CODE {
        return (!valid_test_name(&row.name))
            .then(|| location_fault(code, row.line, row.column))
            .into_iter()
            .collect();
    }
    let Some(parametrize) = &row.parametrize else {
        return (code == TEST_DATACLASS_PARAMETRIZE_CODE)
            .then(|| location_fault(code, row.line, row.column))
            .into_iter()
            .collect();
    };
    let fault = match code {
        TEST_ACCEPTS_TEST_CASE_CODE => !row
            .parameter_names
            .iter()
            .any(|name| name == TEST_CASE_NAME),
        TEST_CASE_ANNOTATION_CODE => {
            !row.parameter_names
                .iter()
                .any(|name| name == TEST_CASE_NAME)
                || !row
                    .test_case_annotation_name
                    .as_ref()
                    .is_some_and(|name| local_types.contains(name))
        }
        TEST_EXPECTED_FIELD_ASSERTION_CODE => !row.references_expected_field,
        TEST_PARAMETRIZE_ARGUMENTS_CODE => {
            parametrize.argument_count < TEST_MINIMUM_PARAMETRIZE_ARGUMENTS
        }
        TEST_PARAMETRIZE_TEST_CASE_CODE => {
            parametrize.argument_count >= TEST_MINIMUM_PARAMETRIZE_ARGUMENTS
                && parametrize.parameter_name.as_deref() != Some(TEST_CASE_NAME)
        }
        TEST_PARAMETRIZE_IDS_CODE => {
            parametrize.argument_count >= TEST_MINIMUM_PARAMETRIZE_ARGUMENTS
                && !parametrize.ids_present
        }
        TEST_INLINE_PARAMETRIZE_VALUES_CODE => {
            parametrize.argument_count >= TEST_MINIMUM_PARAMETRIZE_ARGUMENTS
                && !parametrize.values_is_sequence
                && !parametrize.values_is_comprehension
        }
        TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE => {
            parametrize.argument_count >= TEST_MINIMUM_PARAMETRIZE_ARGUMENTS
                && parametrize.values_is_sequence
                && parametrize.values_empty
        }
        TEST_DESCRIPTION_LAMBDA_IDS_CODE => description_ids_fault(parametrize),
        _ => false,
    };
    if code == TEST_NO_DICT_TEST_CASES_CODE {
        return dictionary_case_faults(code, parametrize);
    }
    if code == TEST_LOCAL_TEST_CASE_CONSTRUCTORS_CODE {
        return local_constructor_faults(code, parametrize, local_types);
    }
    fault
        .then(|| location_fault(code, row.line, row.column))
        .into_iter()
        .collect()
}

fn local_constructor_faults(
    code: &str,
    row: &ParametrizeRow,
    local_types: &std::collections::HashSet<String>,
) -> Vec<NativeFaultRow> {
    if row.argument_count < TEST_MINIMUM_PARAMETRIZE_ARGUMENTS
        || (!row.values_is_sequence && !row.values_is_comprehension)
    {
        return Vec::new();
    }
    row.cases
        .iter()
        .filter(|case| {
            !case.dictionary
                && !case
                    .constructor_name
                    .as_ref()
                    .is_some_and(|name| local_types.contains(name))
        })
        .map(|case| location_fault(code, case.line, case.column))
        .collect()
}

fn local_test_case_types(
    program: &ProgramHandle,
    context: &NativeRuleContext,
) -> std::collections::HashSet<String> {
    let path = sibling_path(&context.repository_path, TEST_TYPES_FILE);
    let query = NativeProjectQuery {
        kind: "dataclasses".to_owned(),
        path,
        argument: String::new(),
    };
    let declared: std::collections::HashSet<&str> = context
        .observation(&query)
        .iter()
        .map(String::as_str)
        .collect();
    let expected_module = sibling_path(&context.repository_path, "_test_types").replace('/', ".");
    let mut imported = std::collections::HashSet::new();
    for row in &program.reference_rows().imports {
        if row.top_level && row.from_import && row.module_parts.join(".") == expected_module {
            for alias in &row.aliases {
                if declared.contains(alias.imported_name.as_str()) {
                    imported.insert(alias.bound_name.clone());
                }
            }
        }
    }
    imported
}

fn sibling_path(repository_path: &str, name: &str) -> String {
    let parent = repository_path.rsplit_once('/').map_or("", |item| item.0);
    format!("{parent}/{name}")
}

fn observed_bool(context: &NativeRuleContext, kind: &str, path: &str) -> bool {
    context.observation(&NativeProjectQuery {
        kind: kind.to_owned(),
        path: path.to_owned(),
        argument: String::new(),
    }) == ["true"]
}

fn dictionary_case_faults(code: &str, row: &ParametrizeRow) -> Vec<NativeFaultRow> {
    if row.argument_count < TEST_MINIMUM_PARAMETRIZE_ARGUMENTS || !row.values_is_sequence {
        return Vec::new();
    }
    row.cases
        .iter()
        .filter(|case| case.dictionary)
        .map(|case| location_fault(code, case.line, case.column))
        .collect()
}

fn location_faults(code: &str, locations: &[(u32, u32)]) -> Vec<NativeFaultRow> {
    locations
        .iter()
        .map(|(line, column)| location_fault(code, *line, *column))
        .collect()
}

fn location_fault(code: &str, line: u32, column: u32) -> NativeFaultRow {
    NativeFaultRow {
        code: code.to_owned(),
        line,
        column,
        message: None,
        remediation: None,
        path: None,
    }
}

fn path_fault(code: &str, message: Option<&str>) -> NativeFaultRow {
    NativeFaultRow {
        code: code.to_owned(),
        line: 0,
        column: 0,
        message: message.map(str::to_owned),
        remediation: None,
        path: None,
    }
}
