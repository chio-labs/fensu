//! Assemble first-parameter-mutation rows in breadth-first order.

use std::collections::{HashMap, HashSet};

use ruff_python_ast::{Expr, ModModule, Stmt};

use crate::constants;
use crate::facts::helpers::metrics::lookups::{
    function_at, function_positions, is_dunder_name, nonreceiver_parameter_names,
};
use crate::facts::helpers::naming::names::decorator_name;
use crate::facts::helpers::shape::breadth::{breadth_first_from, breadth_first_with_parents};
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::ParameterMutationRow;
use crate::positions::models::LineIndex;

pub(crate) fn parameter_mutation_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<ParameterMutationRow> {
    let (nodes, parents) = breadth_first_with_parents(module);
    let positions = function_positions(&nodes);
    if positions.is_empty() {
        return Vec::new();
    }
    let parameters_by_position: HashMap<usize, HashSet<&str>> = positions
        .iter()
        .filter_map(|position| {
            function_at(&nodes, *position)
                .map(|function| (*position, nonreceiver_parameter_names(function)))
        })
        .collect();
    let mut mutations_by_position: HashMap<usize, Vec<(&str, usize)>> = HashMap::new();
    for (position, node) in nodes.iter().enumerate() {
        let root_names = mutation_root_names(node);
        if root_names.is_empty() {
            continue;
        }
        let mut current = parents[position];
        while let Some(parent_position) = current {
            if let Some(parameter_names) = parameters_by_position.get(&parent_position) {
                let mutated = root_names
                    .iter()
                    .find(|name| parameter_names.contains(*name));
                if let Some(name) = mutated {
                    let entries = mutations_by_position.entry(parent_position).or_default();
                    if !entries.iter().any(|(known, _)| known == name) {
                        entries.push((name, position));
                    }
                }
            }
            current = parents[parent_position];
        }
    }
    let mut returned_by_position: HashMap<usize, HashSet<String>> = mutations_by_position
        .keys()
        .map(|position| (*position, HashSet::new()))
        .collect();
    for (position, node) in nodes.iter().enumerate() {
        let ShapeNode::Stmt(Stmt::Return(inner)) = node else {
            continue;
        };
        let Some(value) = inner.value.as_deref() else {
            continue;
        };
        let returned_names = name_identifiers(value);
        let mut current = parents[position];
        while let Some(parent_position) = current {
            if let Some(names) = returned_by_position.get_mut(&parent_position) {
                names.extend(returned_names.iter().cloned());
            }
            current = parents[parent_position];
        }
    }
    let mut rows: Vec<ParameterMutationRow> = Vec::new();
    for position in &positions {
        let Some(function) = function_at(&nodes, *position) else {
            continue;
        };
        let Some(entries) = mutations_by_position.get(position) else {
            continue;
        };
        let empty: HashSet<String> = HashSet::new();
        let returned_names = returned_by_position.get(position).unwrap_or(&empty);
        let setter = function.decorator_list.iter().any(|decorator| {
            decorator_name(&decorator.expression).ends_with(constants::SETTER_DECORATOR_SUFFIX)
        });
        for (parameter_name, mutation_position) in entries {
            let (line, column) = start_of(&nodes[*mutation_position], index, source);
            rows.push(ParameterMutationRow {
                function_name: function.name.as_str().to_owned(),
                parameter_name: (*parameter_name).to_owned(),
                line,
                column,
                returned: returned_names.contains(*parameter_name),
                dunder: is_dunder_name(function.name.as_str()),
                setter,
            });
        }
    }
    rows
}

fn mutation_root_names<'a>(node: &ShapeNode<'a>) -> Vec<&'a str> {
    let (targets, is_call): (Vec<&'a Expr>, bool) = match node {
        ShapeNode::Stmt(Stmt::Assign(inner)) => (inner.targets.iter().collect(), false),
        ShapeNode::Stmt(Stmt::AnnAssign(inner)) => (vec![&inner.target], false),
        ShapeNode::Stmt(Stmt::AugAssign(inner)) => (vec![&inner.target], false),
        ShapeNode::Expr(Expr::Call(call)) if is_mutator_call(call) => match &*call.func {
            Expr::Attribute(attribute) => (vec![&attribute.value], true),
            _ => (Vec::new(), true),
        },
        _ => return Vec::new(),
    };
    let mut names: Vec<&'a str> = Vec::new();
    for target in targets {
        if matches!(target, Expr::Name(_)) && !is_call {
            continue;
        }
        if let Some(name) = attribute_root_name(target) {
            names.push(name);
        }
    }
    names
}

pub(crate) fn is_mutator_call(call: &ruff_python_ast::ExprCall) -> bool {
    match &*call.func {
        Expr::Attribute(attribute) => {
            constants::MUTATOR_METHOD_NAMES.contains(&attribute.attr.as_str())
        }
        _ => false,
    }
}

pub(crate) fn attribute_root_name(expression: &Expr) -> Option<&str> {
    let mut current = expression;
    loop {
        match current {
            Expr::Attribute(attribute) => current = &attribute.value,
            Expr::Subscript(subscript) => current = &subscript.value,
            Expr::Name(name) => return Some(name.id.as_str()),
            _ => return None,
        }
    }
}

fn name_identifiers(value: &Expr) -> HashSet<String> {
    let mut names: HashSet<String> = HashSet::new();
    for node in breadth_first_from(ShapeNode::Expr(value)) {
        if let ShapeNode::Expr(Expr::Name(name)) = node {
            names.insert(name.id.as_str().to_owned());
        }
    }
    names
}
