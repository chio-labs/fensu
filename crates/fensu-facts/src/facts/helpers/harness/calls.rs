//! Evaluate-rule harness call extraction.

use std::collections::{HashMap, HashSet};

use ruff_python_ast::{Expr, ExprCall, ModModule, Stmt, StmtFunctionDef};

use crate::constants;
use crate::facts::helpers::harness::dimensions::dimension_rows;
use crate::facts::helpers::harness::imports::{
    all_parameter_names, expression_parts, function_shadowed_names, index_module_bindings,
    BindingIndex,
};
use crate::facts::helpers::shape::breadth::breadth_first_with_parents;
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::{DimensionRow, EvaluateRuleCallRow};
use crate::positions::models::LineIndex;

struct CallContext<'context, 'module> {
    nodes: &'context [ShapeNode<'module>],
    bindings: &'context BindingIndex<'module>,
    index: &'context LineIndex,
    source: &'context str,
}

pub(crate) fn evaluate_rule_call_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<EvaluateRuleCallRow> {
    let bindings = index_module_bindings(module);
    let (nodes, parents) = breadth_first_with_parents(module);
    let mut dimension_cache: HashMap<usize, Vec<DimensionRow>> = HashMap::new();
    let mut shadow_cache: HashMap<usize, HashSet<&str>> = HashMap::new();
    let mut rows: Vec<EvaluateRuleCallRow> = Vec::new();
    let context = CallContext {
        nodes: &nodes,
        bindings: &bindings,
        index,
        source,
    };
    for (position, node) in nodes.iter().enumerate() {
        let ShapeNode::Expr(Expr::Call(call)) = node else {
            continue;
        };
        let owner_position = test_owner_position(&nodes, &parents, position);
        let no_shadowed_names: HashSet<&str> = HashSet::new();
        let shadowed = match owner_position {
            Some(owner) => shadow_cache
                .entry(owner)
                .or_insert_with(|| owner_shadowed_names(&nodes, owner)),
            None => &no_shadowed_names,
        };
        let is_harness_call = bindings
            .resolve_expression(&call.func, shadowed)
            .is_some_and(|reference| {
                reference.module_name == constants::FENSU_MODULE_NAME
                    && reference.symbol_name == constants::EVALUATE_RULE_NAME
            });
        if !is_harness_call {
            continue;
        }
        rows.push(call_row(
            call,
            node,
            owner_position,
            shadowed,
            &mut dimension_cache,
            &context,
        ));
    }
    rows
}

fn test_owner_position(
    nodes: &[ShapeNode<'_>],
    parents: &[Option<usize>],
    position: usize,
) -> Option<usize> {
    let mut current = parents[position];
    while let Some(parent_position) = current {
        match &nodes[parent_position] {
            ShapeNode::Expr(Expr::Lambda(_)) | ShapeNode::Stmt(Stmt::ClassDef(_)) => return None,
            ShapeNode::Stmt(Stmt::FunctionDef(function)) => {
                if function
                    .name
                    .as_str()
                    .starts_with(constants::TEST_FUNCTION_PREFIX)
                {
                    return Some(parent_position);
                }
                return None;
            }
            _ => {}
        }
        current = parents[parent_position];
    }
    None
}

fn owner_shadowed_names<'a>(nodes: &[ShapeNode<'a>], owner: usize) -> HashSet<&'a str> {
    match &nodes[owner] {
        ShapeNode::Stmt(statement) => match statement {
            Stmt::FunctionDef(function) => function_shadowed_names(statement, function),
            _ => HashSet::new(),
        },
        _ => HashSet::new(),
    }
}

fn owner_function<'a>(nodes: &[ShapeNode<'a>], owner: usize) -> Option<&'a StmtFunctionDef> {
    match &nodes[owner] {
        ShapeNode::Stmt(Stmt::FunctionDef(function)) => Some(function),
        _ => None,
    }
}

fn call_row<'module>(
    call: &ExprCall,
    node: &ShapeNode<'module>,
    owner_position: Option<usize>,
    shadowed: &HashSet<&str>,
    dimension_cache: &mut HashMap<usize, Vec<DimensionRow>>,
    context: &CallContext<'_, 'module>,
) -> EvaluateRuleCallRow {
    let rule_expression = keyword_value(call, constants::RULE_KEYWORD_NAME);
    let test_case_expression = keyword_value(call, constants::TEST_CASE_KEYWORD_NAME);
    let (form, case_locations, unknown) = test_case_fact(
        test_case_expression,
        owner_position,
        shadowed,
        dimension_cache,
        context,
    );
    let (line, column) = start_of(node, context.index, context.source);
    let owner = owner_position.and_then(|position| owner_function(context.nodes, position));
    EvaluateRuleCallRow {
        line,
        column,
        test_function_name: owner.map(|function| function.name.as_str().to_owned()),
        test_function_location: owner_position
            .map(|position| start_of(&context.nodes[position], context.index, context.source)),
        rule_expression: rule_expression.and_then(owned_expression_parts),
        rule_location: rule_expression.map(|expression| {
            start_of(&ShapeNode::Expr(expression), context.index, context.source)
        }),
        rule_reference: rule_expression
            .and_then(|expression| context.bindings.resolve_expression(expression, shadowed)),
        test_case_expression: test_case_expression.and_then(owned_expression_parts),
        test_case_location: test_case_expression.map(|expression| {
            start_of(&ShapeNode::Expr(expression), context.index, context.source)
        }),
        test_case_form: form.to_owned(),
        case_locations,
        unknown_case_count: unknown,
    }
}

fn test_case_fact<'module>(
    expression: Option<&Expr>,
    owner_position: Option<usize>,
    shadowed: &HashSet<&str>,
    dimension_cache: &mut HashMap<usize, Vec<DimensionRow>>,
    context: &CallContext<'_, 'module>,
) -> (&'static str, Vec<(u32, u32)>, bool) {
    let Some(inner) = expression else {
        return (constants::MISSING_CASE_FORM, Vec::new(), true);
    };
    if context.bindings.is_rule_case_call(inner, shadowed) {
        return (
            constants::LITERAL_CASE_FORM,
            vec![start_of(
                &ShapeNode::Expr(inner),
                context.index,
                context.source,
            )],
            false,
        );
    }
    let Expr::Name(name) = inner else {
        return (constants::DYNAMIC_CASE_FORM, Vec::new(), true);
    };
    let owner = owner_position.and_then(|position| owner_function(context.nodes, position));
    let named_parameter =
        owner.is_some_and(|function| all_parameter_names(function).contains(&name.id.as_str()));
    if !named_parameter {
        let form = match shadowed.contains(name.id.as_str()) {
            true => constants::LOCAL_CASE_FORM,
            false => constants::DYNAMIC_CASE_FORM,
        };
        return (form, Vec::new(), true);
    }
    let Some(owner_index) = owner_position else {
        return (constants::DYNAMIC_CASE_FORM, Vec::new(), true);
    };
    let Some(function) = owner else {
        return (constants::DYNAMIC_CASE_FORM, Vec::new(), true);
    };
    let dimensions = dimension_cache.entry(owner_index).or_insert_with(|| {
        dimension_rows(function, context.bindings, context.index, context.source)
    });
    let matching: Vec<&DimensionRow> = dimensions
        .iter()
        .filter(|dimension| dimension.parameter_names == [name.id.as_str()])
        .collect();
    if matching.len() != 1 {
        return (constants::PARAMETER_CASE_FORM, Vec::new(), true);
    }
    (
        constants::PARAMETER_CASE_FORM,
        matching[0].rule_case_locations.clone(),
        matching[0].unknown_rule_case_count,
    )
}

fn keyword_value<'a>(call: &'a ExprCall, name: &str) -> Option<&'a Expr> {
    let mut values: Vec<&'a Expr> = Vec::new();
    for keyword in &call.arguments.keywords {
        if keyword
            .arg
            .as_ref()
            .is_some_and(|argument| argument.as_str() == name)
        {
            values.push(&keyword.value);
        }
    }
    match values.len() {
        1 => values.first().copied(),
        _ => None,
    }
}

fn owned_expression_parts(expression: &Expr) -> Option<Vec<String>> {
    expression_parts(expression).map(|parts| parts.into_iter().map(str::to_owned).collect())
}
