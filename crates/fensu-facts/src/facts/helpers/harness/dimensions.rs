//! Parametrize dimension extraction for test functions.

use std::collections::HashSet;

use ruff_python_ast::{Decorator, Expr, StmtFunctionDef};

use crate::constants;
use crate::facts::helpers::harness::imports::{expression_parts, BindingIndex};
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::DimensionRow;
use crate::positions::models::LineIndex;

pub(crate) fn dimension_rows(
    function: &StmtFunctionDef,
    bindings: &BindingIndex<'_>,
    index: &LineIndex,
    source: &str,
) -> Vec<DimensionRow> {
    let mut rows: Vec<DimensionRow> = Vec::new();
    for decorator in &function.decorator_list {
        let Expr::Call(call) = &decorator.expression else {
            continue;
        };
        let is_parametrize = expression_parts(&call.func)
            .is_some_and(|parts| parts == constants::PARAMETRIZE_NAME_PARTS);
        if !is_parametrize {
            continue;
        }
        rows.push(dimension_row(decorator, call, bindings, index, source));
    }
    rows
}

fn dimension_row(
    decorator: &Decorator,
    call: &ruff_python_ast::ExprCall,
    bindings: &BindingIndex<'_>,
    index: &LineIndex,
    source: &str,
) -> DimensionRow {
    let parameter_names: Vec<String> = call
        .arguments
        .args
        .first()
        .map(split_parameter_names)
        .unwrap_or_default();
    let values: Option<&Expr> = (call.arguments.args.len()
        >= constants::MINIMUM_PARAMETRIZE_ARGUMENTS)
        .then(|| &call.arguments.args[1]);
    let decorator_line = index
        .locate(
            ruff_text_size::Ranged::range(&decorator.expression)
                .start()
                .to_usize(),
        )
        .line;
    let sequence = resolved_sequence(values, decorator_line, bindings, index);
    let mut unknown = values.is_some() && sequence.is_none();
    let mut case_locations: Vec<(u32, u32)> = Vec::new();
    if let Some(sequence_expression) = sequence {
        let empty: HashSet<&str> = HashSet::new();
        for element in sequence_elements(sequence_expression) {
            if !bindings.is_rule_case_call(element, &empty) {
                unknown = true;
                case_locations.clear();
                break;
            }
            case_locations.push(start_of(&ShapeNode::Expr(element), index, source));
        }
    }
    let (line, column) = start_of(&ShapeNode::Expr(&decorator.expression), index, source);
    DimensionRow {
        line,
        column,
        parameter_names,
        values_location: values
            .map(|expression| start_of(&ShapeNode::Expr(expression), index, source)),
        rule_case_locations: case_locations,
        unknown_rule_case_count: unknown,
    }
}

pub(crate) fn split_parameter_names(expression: &Expr) -> Vec<String> {
    let Expr::StringLiteral(literal) = expression else {
        return Vec::new();
    };
    literal
        .value
        .to_str()
        .split(',')
        .map(str::trim)
        .filter(|name| !name.is_empty())
        .map(str::to_owned)
        .collect()
}

fn resolved_sequence<'a>(
    expression: Option<&'a Expr>,
    before_line: u32,
    bindings: &BindingIndex<'a>,
    index: &LineIndex,
) -> Option<&'a Expr> {
    let inner = expression?;
    if matches!(inner, Expr::List(_) | Expr::Tuple(_)) {
        return Some(inner);
    }
    let Expr::Name(name) = inner else {
        return None;
    };
    if bindings.from_bindings.contains_key(name.id.as_str()) {
        return None;
    }
    let candidates = bindings.literal_sequences.get(name.id.as_str())?;
    if candidates.len() != 1 {
        return None;
    }
    let candidate = candidates[0];
    let candidate_line = index
        .locate(ruff_text_size::Ranged::range(candidate).start().to_usize())
        .line;
    if candidate_line >= before_line {
        return None;
    }
    Some(candidate)
}

pub(crate) fn sequence_elements(expression: &Expr) -> &[Expr] {
    match expression {
        Expr::List(inner) => &inner.elts,
        Expr::Tuple(inner) => &inner.elts,
        _ => &[],
    }
}
