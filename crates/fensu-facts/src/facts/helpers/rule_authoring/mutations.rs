//! Complete parameter mutation occurrence extraction.

use std::collections::{HashMap, HashSet};

use ruff_python_ast::{Expr, ModModule, Stmt, StmtFunctionDef};

use crate::constants;
use crate::facts::helpers::metrics::lookups::{function_at, function_positions, is_dunder_name};
use crate::facts::helpers::metrics::mutations::{attribute_root_name, is_mutator_call};
use crate::facts::helpers::naming::names::decorator_name;
use crate::facts::helpers::shape::breadth::{breadth_first_from, breadth_first_with_parents};
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::ParameterMutationOccurrenceRow;
use crate::positions::models::LineIndex;

pub(crate) fn parameter_mutation_occurrence_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<ParameterMutationOccurrenceRow> {
    let (nodes, parents) = breadth_first_with_parents(module);
    let positions = function_positions(&nodes);
    let parameters_by_position: HashMap<usize, HashMap<&str, &'static str>> = positions
        .iter()
        .filter_map(|position| {
            function_at(&nodes, *position)
                .map(|function| (*position, nonreceiver_parameter_kinds(function)))
        })
        .collect();
    if parameters_by_position.is_empty() {
        return Vec::new();
    }
    let mut mutations_by_position: HashMap<usize, Vec<(&str, usize)>> = HashMap::new();
    for (position, node) in nodes.iter().enumerate() {
        let root_names = mutation_root_names(node);
        if root_names.is_empty() {
            continue;
        }
        let mut current = parents[position];
        while let Some(parent_position) = current {
            if let Some(parameter_kinds) = parameters_by_position.get(&parent_position) {
                if let Some(name) = root_names
                    .iter()
                    .find(|name| parameter_kinds.contains_key(*name))
                {
                    mutations_by_position
                        .entry(parent_position)
                        .or_default()
                        .push((name, position));
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
    let mut rows = Vec::new();
    for position in positions {
        let Some(function) = function_at(&nodes, position) else {
            continue;
        };
        let Some(entries) = mutations_by_position.get(&position) else {
            continue;
        };
        let empty = HashSet::new();
        let returned_names = returned_by_position.get(&position).unwrap_or(&empty);
        let setter = function.decorator_list.iter().any(|decorator| {
            decorator_name(&decorator.expression).ends_with(constants::SETTER_DECORATOR_SUFFIX)
        });
        for (parameter_name, mutation_position) in entries {
            let (line, column) = start_of(&nodes[*mutation_position], index, source);
            rows.push(ParameterMutationOccurrenceRow {
                function_name: function.name.as_str().to_owned(),
                parameter_name: (*parameter_name).to_owned(),
                parameter_kind: parameters_by_position[&position][parameter_name].to_owned(),
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

fn nonreceiver_parameter_kinds(function: &StmtFunctionDef) -> HashMap<&str, &'static str> {
    let parameters = &function.parameters;
    let mut kinds = HashMap::new();
    for parameter in &parameters.posonlyargs {
        kinds.insert(parameter.parameter.name.id.as_str(), "positional_only");
    }
    for parameter in &parameters.args {
        kinds.insert(
            parameter.parameter.name.id.as_str(),
            "positional_or_keyword",
        );
    }
    for parameter in &parameters.kwonlyargs {
        kinds.insert(parameter.parameter.name.id.as_str(), "keyword_only");
    }
    if let Some(vararg) = &parameters.vararg {
        kinds.insert(vararg.name.id.as_str(), "vararg");
    }
    if let Some(kwarg) = &parameters.kwarg {
        kinds.insert(kwarg.name.id.as_str(), "kwarg");
    }
    for receiver in constants::RECEIVER_NAMES {
        kinds.remove(receiver);
    }
    kinds
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
    let mut names = Vec::new();
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

fn name_identifiers(value: &Expr) -> HashSet<String> {
    let mut names = HashSet::new();
    for node in breadth_first_from(ShapeNode::Expr(value)) {
        if let ShapeNode::Expr(Expr::Name(name)) = node {
            names.insert(name.id.as_str().to_owned());
        }
    }
    names
}
