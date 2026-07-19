//! Naming-contract policy over shared function-contract rows.

use std::collections::HashSet;

use strata_facts::facts::models::FunctionContractRow;

use crate::rules::constants::{
    ITERATOR_NAME_MUST_PRODUCE_ITERATOR_CODE, PREDICATE_MUST_RETURN_BOOL_CODE,
    VALIDATOR_MUST_NOT_RETURN_CODE, VALUE_NAME_MUST_RETURN_VALUE_CODE,
};
use crate::rules::helpers::naming_globs::fnmatchcase;
use crate::rules::models::{NativeFaultRow, NativeRuleContext};

const NO_RETURN: &str = "no-return";
const RETURNS_BOOL: &str = "returns-bool";
const RETURNS_VALUE: &str = "returns-value";
const RETURNS_ITERATOR: &str = "returns-iterator";
const MISSING_CATEGORY: &str = "missing";
const NONE_CATEGORY: &str = "none";
const BOOL_CATEGORIES: &[&str] = &["bool", "type-guard", "type-is"];
const ITERATOR_CATEGORIES: &[&str] =
    &["iterator", "generator", "async-iterator", "async-generator"];

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
enum ContractBehavior {
    NoReturn,
    ReturnsBool,
    ReturnsValue,
    ReturnsIterator,
}

impl ContractBehavior {
    fn parse(value: &str) -> Option<Self> {
        match value {
            NO_RETURN => Some(Self::NoReturn),
            RETURNS_BOOL => Some(Self::ReturnsBool),
            RETURNS_VALUE => Some(Self::ReturnsValue),
            RETURNS_ITERATOR => Some(Self::ReturnsIterator),
            _ => None,
        }
    }

    fn as_str(self) -> &'static str {
        match self {
            Self::NoReturn => NO_RETURN,
            Self::ReturnsBool => RETURNS_BOOL,
            Self::ReturnsValue => RETURNS_VALUE,
            Self::ReturnsIterator => RETURNS_ITERATOR,
        }
    }
}

struct MatchedContract<'a> {
    row: &'a FunctionContractRow,
    behavior: ContractBehavior,
}

pub(crate) fn naming_faults(
    rows: &[FunctionContractRow],
    code: &str,
    context: &NativeRuleContext,
) -> Option<Result<Vec<NativeFaultRow>, String>> {
    let wanted_behavior: ContractBehavior = match code {
        VALIDATOR_MUST_NOT_RETURN_CODE => ContractBehavior::NoReturn,
        PREDICATE_MUST_RETURN_BOOL_CODE => ContractBehavior::ReturnsBool,
        VALUE_NAME_MUST_RETURN_VALUE_CODE => ContractBehavior::ReturnsValue,
        ITERATOR_NAME_MUST_PRODUCE_ITERATOR_CODE => ContractBehavior::ReturnsIterator,
        _ => return None,
    };
    Some(matched_contracts(rows, context).map(|matches| {
        matches
            .into_iter()
            .filter(|matched| matched.behavior == wanted_behavior)
            .filter_map(|matched| fault_for(code, matched.row))
            .collect()
    }))
}

fn matched_contracts<'a>(
    rows: &'a [FunctionContractRow],
    context: &NativeRuleContext,
) -> Result<Vec<MatchedContract<'a>>, String> {
    let mut matched: Vec<MatchedContract<'a>> = Vec::new();
    for row in rows {
        let mut pattern_behaviors: Vec<(&str, ContractBehavior)> = context
            .contracts
            .iter()
            .filter_map(|(pattern, behavior)| {
                let behavior = ContractBehavior::parse(behavior)?;
                fnmatchcase(&row.function_name, pattern).then_some((pattern.as_str(), behavior))
            })
            .collect();
        pattern_behaviors.sort_by_key(|(pattern, _)| *pattern);
        let behaviors: HashSet<ContractBehavior> = pattern_behaviors
            .iter()
            .map(|(_, behavior)| *behavior)
            .collect();
        if behaviors.len() > 1 {
            let details: String = pattern_behaviors
                .iter()
                .map(|(pattern, behavior)| format!("'{pattern}' ({})", behavior.as_str()))
                .collect::<Vec<_>>()
                .join(", ");
            return Err(format!(
                "Conflicting contracts for function '{}' at {}: {details}.",
                row.function_name, context.repository_path
            ));
        }
        if let Some(behavior) = behaviors.into_iter().next() {
            matched.push(MatchedContract { row, behavior });
        }
    }
    Ok(matched)
}

fn fault_for(code: &str, row: &FunctionContractRow) -> Option<NativeFaultRow> {
    match code {
        VALIDATOR_MUST_NOT_RETURN_CODE => validator_fault(row),
        PREDICATE_MUST_RETURN_BOOL_CODE => predicate_fault(row),
        VALUE_NAME_MUST_RETURN_VALUE_CODE => value_fault(row),
        ITERATOR_NAME_MUST_PRODUCE_ITERATOR_CODE => iterator_fault(row),
        _ => None,
    }
}

fn validator_fault(row: &FunctionContractRow) -> Option<NativeFaultRow> {
    let (line, column) = row.meaningful_return?;
    Some(NativeFaultRow {
        code: VALIDATOR_MUST_NOT_RETURN_CODE.to_owned(),
        line,
        column,
        message: Some(format!(
            "function '{}' uses a no-return name but returns a meaningful value",
            row.function_name
        )),
        remediation: Some(
            "Remove the meaningful return and raise on invalid input, or rename the \
value-producing function as a query such as is_valid or get_validation_result."
                .to_owned(),
        ),
        path: None,
    })
}

fn predicate_fault(row: &FunctionContractRow) -> Option<NativeFaultRow> {
    if row.category == MISSING_CATEGORY || BOOL_CATEGORIES.contains(&row.category.as_str()) {
        return None;
    }
    Some(NativeFaultRow {
        code: PREDICATE_MUST_RETURN_BOOL_CODE.to_owned(),
        line: row.line,
        column: row.column,
        message: Some(format!(
            "function '{}' uses a predicate name but declares '{}'",
            row.function_name,
            annotation(row)
        )),
        remediation: Some(predicate_remediation(&row.function_name)),
        path: None,
    })
}

fn value_fault(row: &FunctionContractRow) -> Option<NativeFaultRow> {
    if row.category != NONE_CATEGORY {
        return None;
    }
    Some(NativeFaultRow {
        code: VALUE_NAME_MUST_RETURN_VALUE_CODE.to_owned(),
        line: row.line,
        column: row.column,
        message: Some(format!(
            "function '{}' uses a value-producing name but declares '{}'",
            row.function_name,
            annotation(row)
        )),
        remediation: Some(value_remediation(&row.function_name)),
        path: None,
    })
}

fn iterator_fault(row: &FunctionContractRow) -> Option<NativeFaultRow> {
    if row.contains_yield
        || row.category == MISSING_CATEGORY
        || ITERATOR_CATEGORIES.contains(&row.category.as_str())
    {
        return None;
    }
    let suffix: &str = row
        .function_name
        .strip_prefix("iter_")
        .unwrap_or(&row.function_name);
    Some(NativeFaultRow {
        code: ITERATOR_NAME_MUST_PRODUCE_ITERATOR_CODE.to_owned(),
        line: row.line,
        column: row.column,
        message: Some(format!(
            "function '{}' uses an iterator name but declares '{}'",
            row.function_name,
            annotation(row)
        )),
        remediation: Some(format!(
            "Return an iterator or generator, or rename an eager collection function with a \
name such as collect_{suffix}."
        )),
        path: None,
    })
}

fn annotation(row: &FunctionContractRow) -> &str {
    row.annotation.as_deref().unwrap_or("missing")
}

fn predicate_remediation(function_name: &str) -> String {
    let rename: String = if let Some(suffix) = function_name.strip_prefix("has_") {
        format!("count_{suffix}")
    } else if let Some(suffix) = function_name.strip_prefix("can_") {
        format!("explain_{suffix} or {suffix}_reason")
    } else if let Some(suffix) = function_name.strip_prefix("supports_") {
        format!("supported_{suffix} or capabilities")
    } else {
        let suffix = function_name.strip_prefix("is_").unwrap_or(function_name);
        format!("read_{suffix} or current_{suffix}")
    };
    format!(
        "Return bool (or TypeGuard/TypeIs), or rename the function to describe the value it \
returns, such as {rename}."
    )
}

fn value_remediation(function_name: &str) -> String {
    if function_name.starts_with("get_") {
        return "Return the queried value (including an optional value when absence is valid), or \
rename a command for its action, such as initialize_cache, populate_cache, or update_cache."
            .to_owned();
    }
    "Return the converted representation, or rename a side-effecting operation to describe its \
destination, such as write_json or export_json."
        .to_owned()
}
