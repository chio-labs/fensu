//! Per-function parametrization and local test-case policy.

use std::collections::HashSet;

use fensu_facts::extension::models::ProgramHandle;
use fensu_facts::facts::models::{ParametrizeRow, TestFunctionRow};

use crate::rules::_helpers::generated_policy::{
    FFT405_MINIMUM_PARAMETRIZE_ARGUMENTS, FFT406_MINIMUM_PARAMETRIZE_ARGUMENTS,
    FFT407_MINIMUM_PARAMETRIZE_ARGUMENTS, FFT408_MINIMUM_PARAMETRIZE_ARGUMENTS,
    FFT411_MINIMUM_PARAMETRIZE_ARGUMENTS, FFT412_MINIMUM_PARAMETRIZE_ARGUMENTS,
    FFT413_MINIMUM_PARAMETRIZE_ARGUMENTS, FFT414_MINIMUM_PARAMETRIZE_ARGUMENTS,
};
use crate::rules::_helpers::test_names::{description_ids_fault, valid_test_name};
use crate::rules::constants::{
    TEST_ACCEPTS_TEST_CASE_CODE, TEST_CASE_ANNOTATION_CODE, TEST_DATACLASS_PARAMETRIZE_CODE,
    TEST_DESCRIPTION_LAMBDA_IDS_CODE, TEST_EXPECTED_FIELD_ASSERTION_CODE, TEST_FUNCTION_NAME_CODE,
    TEST_INLINE_PARAMETRIZE_VALUES_CODE, TEST_LOCAL_TEST_CASE_CONSTRUCTORS_CODE,
    TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE, TEST_NO_DICT_TEST_CASES_CODE,
    TEST_PARAMETRIZE_ARGUMENTS_CODE, TEST_PARAMETRIZE_IDS_CODE, TEST_PARAMETRIZE_TEST_CASE_CODE,
};
use crate::rules::models::{NativeFaultRow, NativeProjectQuery, NativeRuleContext};

const TEST_CASE_NAME: &str = "test_case";
const TEST_TYPES_FILE: &str = "_test_types.py";

pub(super) fn test_function_faults(
    code: &str,
    row: &TestFunctionRow,
    local_types: &HashSet<String>,
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
    let minimum_arguments = minimum_parametrize_arguments(code);
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
        TEST_PARAMETRIZE_ARGUMENTS_CODE => parametrize.argument_count < minimum_arguments,
        TEST_PARAMETRIZE_TEST_CASE_CODE => {
            parametrize.argument_count >= minimum_arguments
                && parametrize.parameter_name.as_deref() != Some(TEST_CASE_NAME)
        }
        TEST_PARAMETRIZE_IDS_CODE => {
            parametrize.argument_count >= minimum_arguments && !parametrize.ids_present
        }
        TEST_INLINE_PARAMETRIZE_VALUES_CODE => {
            parametrize.argument_count >= minimum_arguments
                && !parametrize.values_is_sequence
                && !parametrize.values_is_comprehension
        }
        TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE => {
            parametrize.argument_count >= minimum_arguments
                && parametrize.values_is_sequence
                && parametrize.values_empty
        }
        TEST_DESCRIPTION_LAMBDA_IDS_CODE => description_ids_fault(parametrize, minimum_arguments),
        _ => false,
    };
    if code == TEST_NO_DICT_TEST_CASES_CODE {
        return dictionary_case_faults(code, parametrize, minimum_arguments);
    }
    if code == TEST_LOCAL_TEST_CASE_CONSTRUCTORS_CODE {
        return local_constructor_faults(code, parametrize, local_types, minimum_arguments);
    }
    fault
        .then(|| location_fault(code, row.line, row.column))
        .into_iter()
        .collect()
}

pub(super) fn local_test_case_types(
    program: &ProgramHandle,
    context: &NativeRuleContext,
) -> HashSet<String> {
    let path = sibling_path(&context.repository_path, TEST_TYPES_FILE);
    let query = NativeProjectQuery {
        kind: "dataclasses".to_owned(),
        path,
        argument: String::new(),
    };
    let declared: HashSet<&str> = context
        .observation(&query)
        .iter()
        .map(String::as_str)
        .collect();
    let expected_module = sibling_path(&context.repository_path, "_test_types").replace('/', ".");
    let mut imported: HashSet<String> = HashSet::new();
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

fn local_constructor_faults(
    code: &str,
    row: &ParametrizeRow,
    local_types: &HashSet<String>,
    minimum_arguments: u32,
) -> Vec<NativeFaultRow> {
    if row.argument_count < minimum_arguments
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

fn dictionary_case_faults(
    code: &str,
    row: &ParametrizeRow,
    minimum_arguments: u32,
) -> Vec<NativeFaultRow> {
    if row.argument_count < minimum_arguments || !row.values_is_sequence {
        return Vec::new();
    }
    row.cases
        .iter()
        .filter(|case| case.dictionary)
        .map(|case| location_fault(code, case.line, case.column))
        .collect()
}

fn minimum_parametrize_arguments(code: &str) -> u32 {
    let value = match code {
        TEST_PARAMETRIZE_ARGUMENTS_CODE => FFT405_MINIMUM_PARAMETRIZE_ARGUMENTS,
        TEST_PARAMETRIZE_TEST_CASE_CODE => FFT406_MINIMUM_PARAMETRIZE_ARGUMENTS,
        TEST_PARAMETRIZE_IDS_CODE => FFT407_MINIMUM_PARAMETRIZE_ARGUMENTS,
        TEST_INLINE_PARAMETRIZE_VALUES_CODE => FFT408_MINIMUM_PARAMETRIZE_ARGUMENTS,
        TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE => FFT411_MINIMUM_PARAMETRIZE_ARGUMENTS,
        TEST_NO_DICT_TEST_CASES_CODE => FFT412_MINIMUM_PARAMETRIZE_ARGUMENTS,
        TEST_LOCAL_TEST_CASE_CONSTRUCTORS_CODE => FFT413_MINIMUM_PARAMETRIZE_ARGUMENTS,
        TEST_DESCRIPTION_LAMBDA_IDS_CODE => FFT414_MINIMUM_PARAMETRIZE_ARGUMENTS,
        _ => 0,
    };
    u32::try_from(value).unwrap_or(u32::MAX)
}

fn sibling_path(repository_path: &str, name: &str) -> String {
    let parent = repository_path.rsplit_once('/').map_or("", |item| item.0);
    format!("{parent}/{name}")
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
