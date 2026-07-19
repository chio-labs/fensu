//! Extract function signatures and statement-local receiver state.

use ruff_python_ast::{Expr, Parameter, Stmt, StmtFunctionDef};

use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::mapping::helpers::expressions::{assigned_names, expression_row, owned_calls};
use crate::facts::mapping::models::{
    MappingExpressionRow, MappingFunctionRow, MappingParameterRow, MappingStatementRow,
};
use crate::positions::models::LineIndex;

pub(crate) fn function_row(
    function: &StmtFunctionDef,
    owning_class: Option<&str>,
    index: &LineIndex,
    source: &str,
) -> MappingFunctionRow {
    let node = ShapeNode::Stmt(&Stmt::FunctionDef(function.clone()));
    let (line, _) = start_of(&node, index, source);
    let parameters = ordered_parameters(function)
        .into_iter()
        .map(|parameter| MappingParameterRow {
            name: parameter.name.id.as_str().to_owned(),
            annotation: parameter
                .annotation
                .as_deref()
                .map(|expression| expression_row(expression, source)),
        })
        .collect();
    MappingFunctionRow {
        name: function.name.as_str().to_owned(),
        line,
        owning_class: owning_class.map(str::to_owned),
        parameters,
        returns: function
            .returns
            .as_deref()
            .map(|expression| expression_row(expression, source)),
        statements: function
            .body
            .iter()
            .map(|statement| statement_row(statement, index, source))
            .collect(),
    }
}

fn ordered_parameters(function: &StmtFunctionDef) -> Vec<&Parameter> {
    let parameters = &function.parameters;
    let mut ordered = Vec::new();
    for parameter in parameters.posonlyargs.iter().chain(&parameters.args) {
        ordered.push(&parameter.parameter);
    }
    for parameter in &parameters.kwonlyargs {
        ordered.push(&parameter.parameter);
    }
    if let Some(parameter) = &parameters.vararg {
        ordered.push(parameter);
    }
    if let Some(parameter) = &parameters.kwarg {
        ordered.push(parameter);
    }
    ordered
}

fn statement_row(statement: &Stmt, index: &LineIndex, source: &str) -> MappingStatementRow {
    let (binding_name, binding_annotation, binding_value) = direct_binding(statement, source);
    MappingStatementRow {
        control_flow: matches!(
            statement,
            Stmt::If(_)
                | Stmt::For(_)
                | Stmt::While(_)
                | Stmt::Try(_)
                | Stmt::With(_)
                | Stmt::Match(_)
        ),
        assigned_names: assigned_names(statement),
        binding_name,
        binding_annotation,
        binding_value,
        calls: owned_calls(ShapeNode::Stmt(statement), index, source),
    }
}

fn direct_binding(
    statement: &Stmt,
    source: &str,
) -> (
    Option<String>,
    Option<MappingExpressionRow>,
    Option<MappingExpressionRow>,
) {
    match statement {
        Stmt::AnnAssign(inner) => match &*inner.target {
            Expr::Name(name) => (
                Some(name.id.as_str().to_owned()),
                Some(expression_row(&inner.annotation, source)),
                inner
                    .value
                    .as_deref()
                    .map(|expression| expression_row(expression, source)),
            ),
            _ => (None, None, None),
        },
        Stmt::Assign(inner) if inner.targets.len() == 1 => match &inner.targets[0] {
            Expr::Name(name) => (
                Some(name.id.as_str().to_owned()),
                None,
                Some(expression_row(&inner.value, source)),
            ),
            _ => (None, None, None),
        },
        Stmt::AugAssign(inner) => match &*inner.target {
            Expr::Name(name) => (Some(name.id.as_str().to_owned()), None, None),
            _ => (None, None, None),
        },
        _ => (None, None, None),
    }
}
