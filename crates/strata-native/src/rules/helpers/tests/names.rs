//! Stable pytest function-name and ids decisions.

use strata_facts::facts::models::ParametrizeRow;

use crate::rules::constants::TEST_MINIMUM_PARAMETRIZE_ARGUMENTS;

pub(crate) fn valid_test_name(name: &str) -> bool {
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

pub(crate) fn description_ids_fault(row: &ParametrizeRow) -> bool {
    row.argument_count >= TEST_MINIMUM_PARAMETRIZE_ARGUMENTS
        && (row.values_is_sequence || row.values_is_comprehension)
        && !row.description_lambda_ids
}
