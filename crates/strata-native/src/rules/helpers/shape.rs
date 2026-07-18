//! Shape-family policy over shared fact rows.

use strata_facts::extension::models::ProgramHandle;

use crate::rules::constants::{
    DEFAULT_MUTATION_RETURN_CODE, KEYWORD_ONLY_ARGUMENTS_CODE, MAX_ARGUMENTS_CODE,
    MAX_STATEMENTS_GLOBAL_CODE, MUTABLE_RESULT_MODEL_CODE, NO_COMPLEX_COMPREHENSIONS_CODE,
    NO_OUTER_STATE_MUTATION_CODE, PARAMETER_MUTATION_IN_PHASE_HELPERS_CODE,
    TOO_MANY_DISTINCT_CALLS_CODE, TOO_MANY_LOCALS_CODE, TOO_MANY_STATEMENTS_CODE,
};
use crate::rules::models::{NativeFaultRow, NativeRuleContext};

const MAX_ARGUMENTS_THRESHOLD: &str = "max_arguments";
const MAX_DISTINCT_CALLS_THRESHOLD: &str = "max_distinct_calls";
const MAX_LOCALS_THRESHOLD: &str = "max_locals";
const MAX_POSITIONAL_ARGS_THRESHOLD: &str = "max_positional_args";
const MAX_STATEMENTS_THRESHOLD: &str = "max_statements";
const MAX_STATEMENTS_GLOBAL_THRESHOLD: &str = "max_statements_global";

pub(crate) fn shape_faults(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Option<Vec<NativeFaultRow>> {
    let faults = match code {
        TOO_MANY_STATEMENTS_CODE => main_metric_faults(
            program,
            code,
            context,
            MAX_STATEMENTS_THRESHOLD,
            |row| row.statement_count,
            |count| format!("function has {count} statements"),
        ),
        TOO_MANY_DISTINCT_CALLS_CODE => main_metric_faults(
            program,
            code,
            context,
            MAX_DISTINCT_CALLS_THRESHOLD,
            |row| row.distinct_call_count,
            |count| format!("function calls {count} distinct functions"),
        ),
        TOO_MANY_LOCALS_CODE => main_metric_faults(
            program,
            code,
            context,
            MAX_LOCALS_THRESHOLD,
            |row| row.assigned_local_count,
            |count| format!("function defines {count} local variables"),
        ),
        MAX_ARGUMENTS_CODE => all_metric_faults(
            program,
            code,
            context,
            MAX_ARGUMENTS_THRESHOLD,
            |row| row.parameter_count,
            |row, limit| row.parameter_count > limit,
            |count, _| format!("function has {count} parameters"),
        ),
        MAX_STATEMENTS_GLOBAL_CODE => global_statement_faults(program, code, context),
        PARAMETER_MUTATION_IN_PHASE_HELPERS_CODE => {
            if context.role.as_deref() != Some("helpers") {
                Vec::new()
            } else {
                program
                    .parameter_mutation_rows()
                    .iter()
                    .filter(|row| !row.dunder && !row.setter)
                    .map(|row| location_fault(code, row.line, row.column))
                    .collect()
            }
        }
        DEFAULT_MUTATION_RETURN_CODE => program
            .parameter_mutation_rows()
            .iter()
            .filter(|row| !row.dunder && !row.setter && !row.returned)
            .map(|row| location_fault(code, row.line, row.column))
            .collect(),
        KEYWORD_ONLY_ARGUMENTS_CODE => all_metric_faults(
            program,
            code,
            context,
            MAX_POSITIONAL_ARGS_THRESHOLD,
            |row| row.parameter_count,
            |row, limit| {
                !row.dunder && row.parameter_count > limit && row.positional_parameter_count > 0
            },
            |count, row| {
                format!(
                    "function with {count} parameters has {} positional parameters",
                    row.positional_parameter_count
                )
            },
        ),
        NO_OUTER_STATE_MUTATION_CODE => program
            .outer_state_mutation_rows()
            .iter()
            .map(|row| location_fault(code, row.start_line, row.start_column))
            .collect(),
        NO_COMPLEX_COMPREHENSIONS_CODE => program
            .control_flow_rows()
            .complex_comprehensions
            .iter()
            .map(|(line, column)| location_fault(code, *line, *column))
            .collect(),
        MUTABLE_RESULT_MODEL_CODE => {
            if context.role.as_deref() != Some("models") {
                Vec::new()
            } else {
                program
                    .dataclass_rows()
                    .iter()
                    .filter(|row| row.shape_candidate && !row.frozen)
                    .map(|row| location_fault(code, row.line, row.column))
                    .collect()
            }
        }
        _ => return None,
    };
    Some(faults)
}

fn main_metric_faults<Metric, Message>(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
    threshold: &str,
    metric: Metric,
    message: Message,
) -> Vec<NativeFaultRow>
where
    Metric: Fn(&strata_facts::facts::models::FunctionMetricRow) -> u32,
    Message: Fn(u32) -> String,
{
    if !context.is_main_module {
        return Vec::new();
    }
    let Some(limit) = context.thresholds.get(threshold).copied() else {
        return Vec::new();
    };
    let (rows, top_level_slots) = program.function_rows();
    top_level_slots
        .iter()
        .filter_map(|slot| rows.get(*slot))
        .filter_map(|row| {
            let count = metric(row);
            (count > limit).then(|| metric_fault(code, row, message(count)))
        })
        .collect()
}

fn all_metric_faults<Metric, Predicate, Message>(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
    threshold: &str,
    metric: Metric,
    predicate: Predicate,
    message: Message,
) -> Vec<NativeFaultRow>
where
    Metric: Fn(&strata_facts::facts::models::FunctionMetricRow) -> u32,
    Predicate: Fn(&strata_facts::facts::models::FunctionMetricRow, u32) -> bool,
    Message: Fn(u32, &strata_facts::facts::models::FunctionMetricRow) -> String,
{
    let Some(limit) = context.thresholds.get(threshold).copied() else {
        return Vec::new();
    };
    program
        .function_rows()
        .0
        .iter()
        .filter(|row| predicate(row, limit))
        .map(|row| metric_fault(code, row, message(metric(row), row)))
        .collect()
}

fn global_statement_faults(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    let Some(limit) = context
        .thresholds
        .get(MAX_STATEMENTS_GLOBAL_THRESHOLD)
        .copied()
    else {
        return Vec::new();
    };
    let (rows, top_level_slots) = program.function_rows();
    rows.iter()
        .enumerate()
        .filter(|(slot, row)| {
            row.statement_count > limit
                && !(context.is_main_module && top_level_slots.contains(slot))
        })
        .map(|(_, row)| {
            metric_fault(
                code,
                row,
                format!("function has {} statements", row.statement_count),
            )
        })
        .collect()
}

fn metric_fault(
    code: &str,
    row: &strata_facts::facts::models::FunctionMetricRow,
    message: String,
) -> NativeFaultRow {
    NativeFaultRow {
        code: code.to_owned(),
        line: row.line,
        column: row.column,
        message: Some(message),
    }
}

fn location_fault(code: &str, line: u32, column: u32) -> NativeFaultRow {
    NativeFaultRow {
        code: code.to_owned(),
        line,
        column,
        message: None,
    }
}
