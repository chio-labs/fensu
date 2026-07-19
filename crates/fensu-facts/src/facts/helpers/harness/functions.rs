//! Reusable syntax metadata rows for test functions.

use ruff_python_ast::{Expr, ExprCall, ModModule, Stmt, StmtFunctionDef};

use crate::constants;
use crate::facts::helpers::control::conditionals::test_conditional_rows;
use crate::facts::helpers::harness::dimensions::dimension_rows;
use crate::facts::helpers::harness::imports::index_module_bindings;
use crate::facts::helpers::naming::names::decorator_name;
use crate::facts::helpers::shape::breadth::{breadth_first_from, breadth_first_nodes};
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::{ParametrizeCaseRow, ParametrizeRow, TestFunctionRow};
use crate::positions::models::LineIndex;

pub(crate) fn test_function_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<TestFunctionRow> {
    let bindings = index_module_bindings(module);
    let nodes = breadth_first_nodes(module);
    let mut rows: Vec<TestFunctionRow> = Vec::new();
    for want_async in [false, true] {
        for node in &nodes {
            let ShapeNode::Stmt(statement) = node else {
                continue;
            };
            let Stmt::FunctionDef(function) = statement else {
                continue;
            };
            if function.is_async != want_async {
                continue;
            }
            if !function
                .name
                .as_str()
                .starts_with(constants::TEST_FUNCTION_PREFIX)
            {
                continue;
            }
            let (line, column) = start_of(node, index, source);
            rows.push(TestFunctionRow {
                name: function.name.as_str().to_owned(),
                line,
                column,
                parameter_names: plain_argument_names(function),
                test_case_annotation_name: test_case_annotation_name(function),
                parametrize: parametrize_row(function, index, source),
                references_expected_field: references_expected_field(statement),
                conditional_locations: test_conditional_rows(&[statement], index, source),
                dimensions: dimension_rows(function, &bindings, index, source),
            });
        }
    }
    rows
}

fn plain_argument_names(function: &StmtFunctionDef) -> Vec<String> {
    function
        .parameters
        .args
        .iter()
        .map(|with_default| with_default.parameter.name.as_str().to_owned())
        .collect()
}

fn test_case_annotation_name(function: &StmtFunctionDef) -> Option<String> {
    let argument = function.parameters.args.iter().find(|with_default| {
        with_default.parameter.name.as_str() == constants::TEST_CASE_KEYWORD_NAME
    })?;
    match argument.parameter.annotation.as_deref() {
        Some(Expr::Name(name)) => Some(name.id.as_str().to_owned()),
        _ => None,
    }
}

fn parametrize_row(
    function: &StmtFunctionDef,
    index: &LineIndex,
    source: &str,
) -> Option<ParametrizeRow> {
    let call: &ExprCall = function
        .decorator_list
        .iter()
        .find_map(|decorator| match &decorator.expression {
            Expr::Call(inner)
                if decorator_name(&inner.func) == constants::PARAMETRIZE_DECORATOR_NAME =>
            {
                Some(inner)
            }
            _ => None,
        })?;
    let ids_expression: Option<&Expr> = call.arguments.keywords.iter().find_map(|keyword| {
        keyword
            .arg
            .as_ref()
            .is_some_and(|name| name.as_str() == constants::IDS_KEYWORD_NAME)
            .then_some(&keyword.value)
    });
    let parameter_name: Option<String> = call.arguments.args.first().and_then(extract_string_value);
    let argument_count = u32::try_from(call.arguments.args.len()).unwrap_or(u32::MAX);
    if call.arguments.args.len() < constants::MINIMUM_PARAMETRIZE_ARGUMENTS {
        return Some(ParametrizeRow {
            argument_count,
            parameter_name,
            ids_present: ids_expression.is_some(),
            description_lambda_ids: is_description_lambda_ids(ids_expression),
            values_is_comprehension: false,
            values_is_sequence: false,
            values_empty: false,
            cases: Vec::new(),
        });
    }
    let values = &call.arguments.args[1];
    let case_nodes: Vec<&Expr> = match values {
        Expr::ListComp(inner) => vec![&inner.elt],
        Expr::SetComp(inner) => vec![&inner.elt],
        Expr::Generator(inner) => vec![&inner.elt],
        Expr::DictComp(inner) => inner
            .key
            .as_deref()
            .map(|key| vec![key])
            .unwrap_or_default(),
        Expr::List(inner) => inner.elts.iter().collect(),
        Expr::Tuple(inner) => inner.elts.iter().collect(),
        _ => Vec::new(),
    };
    let values_is_sequence = matches!(values, Expr::List(_) | Expr::Tuple(_));
    let values_empty = match values {
        Expr::List(inner) => inner.elts.is_empty(),
        Expr::Tuple(inner) => inner.elts.is_empty(),
        _ => false,
    };
    Some(ParametrizeRow {
        argument_count,
        parameter_name,
        ids_present: ids_expression.is_some(),
        description_lambda_ids: is_description_lambda_ids(ids_expression),
        values_is_comprehension: matches!(
            values,
            Expr::ListComp(_) | Expr::SetComp(_) | Expr::DictComp(_) | Expr::Generator(_)
        ),
        values_is_sequence,
        values_empty,
        cases: case_nodes
            .into_iter()
            .map(|case| parametrize_case_row(case, index, source))
            .collect(),
    })
}

fn parametrize_case_row(case: &Expr, index: &LineIndex, source: &str) -> ParametrizeCaseRow {
    let constructor_name = match case {
        Expr::Call(call) => match &*call.func {
            Expr::Name(name) => Some(name.id.as_str().to_owned()),
            _ => None,
        },
        _ => None,
    };
    let (line, column) = start_of(&ShapeNode::Expr(case), index, source);
    ParametrizeCaseRow {
        line,
        column,
        constructor_name,
        dictionary: matches!(case, Expr::Dict(_)),
    }
}

fn extract_string_value(expression: &Expr) -> Option<String> {
    match expression {
        Expr::StringLiteral(literal) => Some(literal.value.to_str().to_owned()),
        _ => None,
    }
}

fn is_description_lambda_ids(expression: Option<&Expr>) -> bool {
    let Some(Expr::Lambda(lambda)) = expression else {
        return false;
    };
    let single_case_parameter = lambda.parameters.as_deref().is_some_and(|parameters| {
        parameters.args.len() == 1
            && parameters.args[0].parameter.name.as_str() == constants::CASE_PARAMETER_NAME
    });
    single_case_parameter
        && attribute_chain(&lambda.body).is_some_and(|chain| {
            chain
                == [
                    constants::CASE_PARAMETER_NAME,
                    constants::DESCRIPTION_ATTRIBUTE_NAME,
                ]
        })
}

fn references_expected_field(statement: &Stmt) -> bool {
    let Stmt::FunctionDef(function) = statement else {
        return false;
    };
    for body_statement in &function.body {
        for node in breadth_first_from(ShapeNode::Stmt(body_statement)) {
            let ShapeNode::Expr(Expr::Attribute(_)) = node else {
                continue;
            };
            let ShapeNode::Expr(expression) = node else {
                continue;
            };
            let Some(chain) = attribute_chain(expression) else {
                continue;
            };
            let matches_expected = chain.len() >= constants::MINIMUM_EXPECTED_FIELD_CHAIN_PARTS
                && chain.first().copied() == Some(constants::TEST_CASE_KEYWORD_NAME)
                && chain
                    .last()
                    .is_some_and(|tail| tail.starts_with(constants::EXPECTED_FIELD_PREFIX));
            if matches_expected {
                return true;
            }
        }
    }
    false
}

fn attribute_chain(expression: &Expr) -> Option<Vec<&str>> {
    let mut parts: Vec<&str> = Vec::new();
    let mut current = expression;
    while let Expr::Attribute(attribute) = current {
        parts.push(attribute.attr.as_str());
        current = &attribute.value;
    }
    let Expr::Name(name) = current else {
        return None;
    };
    parts.push(name.id.as_str());
    parts.reverse();
    Some(parts)
}
