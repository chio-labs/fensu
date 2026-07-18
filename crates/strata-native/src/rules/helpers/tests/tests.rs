//! Tests-family policy over shared per-file fact rows.

use strata_facts::extension::models::ProgramHandle;
use strata_facts::facts::models::{ParametrizeRow, TestFunctionRow};

use crate::rules::constants::{
    TEST_ABSOLUTE_IMPORTS_CODE, TEST_ACCEPTS_TEST_CASE_CODE, TEST_DATACLASS_PARAMETRIZE_CODE,
    TEST_DESCRIPTION_FIELD_NAME, TEST_DESCRIPTION_LAMBDA_IDS_CODE,
    TEST_EXPECTED_FIELD_ASSERTION_CODE, TEST_EXPECTED_FIELD_PREFIX, TEST_FILE_NAME_CODE,
    TEST_FUNCTION_NAME_CODE, TEST_INIT_MODULE_EMPTY_CODE, TEST_INIT_MODULE_NAME,
    TEST_INLINE_PARAMETRIZE_VALUES_CODE, TEST_LOCAL_TEST_TYPES_IMPORT_CODE,
    TEST_MINIMUM_PARAMETRIZE_ARGUMENTS, TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE,
    TEST_NO_COMPLEX_COMPREHENSIONS_CODE, TEST_NO_DICT_TEST_CASES_CODE, TEST_NO_IF_IN_TESTS_CODE,
    TEST_NO_TOP_LEVEL_HELPERS_CODE, TEST_PARAMETRIZE_ARGUMENTS_CODE, TEST_PARAMETRIZE_IDS_CODE,
    TEST_PARAMETRIZE_TEST_CASE_CODE, TEST_PRIVATE_CONSTANT_ORDER_CODE, TEST_TYPES_DESCRIPTION_CODE,
    TEST_TYPES_EXPECTED_FIELD_CODE,
};
use crate::rules::models::{NativeFaultRow, NativeRuleContext};

const TEST_SCOPE: &str = "test";
const TEST_CASE_NAME: &str = "test_case";
const TEST_TYPES_FILE: &str = "_test_types.py";
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
        TEST_FILE_NAME_CODE if test_module && !file_name.starts_with("test_") => {
            vec![path_fault(code, None)]
        }
        code if is_test_function_code(code) && test_module => program
            .test_function_rows()
            .iter()
            .flat_map(|row| test_function_faults(code, row))
            .collect(),
        _ => Vec::new(),
    };
    Some(faults)
}

fn is_test_code(code: &str) -> bool {
    matches!(
        code,
        TEST_INIT_MODULE_EMPTY_CODE
            | TEST_ABSOLUTE_IMPORTS_CODE
            | TEST_NO_TOP_LEVEL_HELPERS_CODE
            | TEST_NO_IF_IN_TESTS_CODE
            | TEST_PRIVATE_CONSTANT_ORDER_CODE
            | TEST_NO_COMPLEX_COMPREHENSIONS_CODE
            | TEST_TYPES_DESCRIPTION_CODE
            | TEST_TYPES_EXPECTED_FIELD_CODE
            | TEST_LOCAL_TEST_TYPES_IMPORT_CODE
            | TEST_FILE_NAME_CODE
            | TEST_FUNCTION_NAME_CODE
            | TEST_DATACLASS_PARAMETRIZE_CODE
            | TEST_ACCEPTS_TEST_CASE_CODE
            | TEST_EXPECTED_FIELD_ASSERTION_CODE
            | TEST_PARAMETRIZE_ARGUMENTS_CODE
            | TEST_PARAMETRIZE_TEST_CASE_CODE
            | TEST_PARAMETRIZE_IDS_CODE
            | TEST_INLINE_PARAMETRIZE_VALUES_CODE
            | TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE
            | TEST_NO_DICT_TEST_CASES_CODE
            | TEST_DESCRIPTION_LAMBDA_IDS_CODE
    )
}

fn is_test_function_code(code: &str) -> bool {
    matches!(
        code,
        TEST_FUNCTION_NAME_CODE
            | TEST_DATACLASS_PARAMETRIZE_CODE
            | TEST_ACCEPTS_TEST_CASE_CODE
            | TEST_EXPECTED_FIELD_ASSERTION_CODE
            | TEST_PARAMETRIZE_ARGUMENTS_CODE
            | TEST_PARAMETRIZE_TEST_CASE_CODE
            | TEST_PARAMETRIZE_IDS_CODE
            | TEST_INLINE_PARAMETRIZE_VALUES_CODE
            | TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE
            | TEST_NO_DICT_TEST_CASES_CODE
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

fn test_function_faults(code: &str, row: &TestFunctionRow) -> Vec<NativeFaultRow> {
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
    fault
        .then(|| location_fault(code, row.line, row.column))
        .into_iter()
        .collect()
}

fn valid_test_name(name: &str) -> bool {
    let Some(after_given) = name.strip_prefix("test_given_") else {
        return false;
    };
    let Some((state, after_when)) = after_given.split_once("_when_") else {
        return false;
    };
    let Some((action, outcome)) = after_when.split_once("_then_") else {
        return false;
    };
    !state.is_empty() && !action.is_empty() && !outcome.is_empty()
}

fn description_ids_fault(row: &ParametrizeRow) -> bool {
    row.argument_count >= TEST_MINIMUM_PARAMETRIZE_ARGUMENTS
        && (row.values_is_sequence || row.values_is_comprehension)
        && !row.description_lambda_ids
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
    }
}

fn path_fault(code: &str, message: Option<&str>) -> NativeFaultRow {
    NativeFaultRow {
        code: code.to_owned(),
        line: 0,
        column: 0,
        message: message.map(str::to_owned),
        remediation: None,
    }
}
