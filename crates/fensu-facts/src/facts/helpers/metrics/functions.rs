//! Assemble structural function-metric rows over the shared arena.

use std::collections::{HashMap, HashSet};

use ruff_python_ast::{Expr, ModModule, Stmt};

use crate::facts::helpers::metrics::lookups::{
    assigned_target_names, dotted_call_name, function_at, function_positions, is_dunder_name,
    nonreceiver_parameter_names,
};
use crate::facts::helpers::shape::breadth::breadth_first_with_parents;
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::FunctionMetricRow;
use crate::positions::models::LineIndex;

pub(crate) fn function_metric_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> (Vec<FunctionMetricRow>, Vec<usize>) {
    let (nodes, parents) = breadth_first_with_parents(module);
    let positions = function_positions(&nodes);
    if positions.is_empty() {
        return (Vec::new(), Vec::new());
    }
    let slot_by_position: HashMap<usize, usize> = positions
        .iter()
        .enumerate()
        .map(|(slot, position)| (*position, slot))
        .collect();
    let mut statement_counts: Vec<u32> = vec![0; positions.len()];
    let mut call_names: Vec<HashSet<String>> = vec![HashSet::new(); positions.len()];
    let mut assigned_names: Vec<HashSet<&str>> = vec![HashSet::new(); positions.len()];
    for (position, node) in nodes.iter().enumerate() {
        let statement = matches!(node, ShapeNode::Stmt(_) | ShapeNode::IfTail(_));
        let call_name: Option<String> = match node {
            ShapeNode::Expr(Expr::Call(call)) => dotted_call_name(&call.func),
            _ => None,
        };
        let target_names = assigned_target_names(node);
        if !statement && call_name.is_none() && target_names.is_empty() {
            continue;
        }
        let mut current = parents[position];
        while let Some(parent_position) = current {
            if let Some(slot) = slot_by_position.get(&parent_position) {
                if statement {
                    statement_counts[*slot] += 1;
                }
                if let Some(name) = &call_name {
                    call_names[*slot].insert(name.clone());
                }
                for target_name in &target_names {
                    assigned_names[*slot].insert(target_name);
                }
            }
            current = parents[parent_position];
        }
    }
    let mut rows: Vec<FunctionMetricRow> = Vec::with_capacity(positions.len());
    for (slot, position) in positions.iter().enumerate() {
        let Some(function) = function_at(&nodes, *position) else {
            continue;
        };
        let (line, column) = start_of(&nodes[*position], index, source);
        let positional_count = function
            .parameters
            .posonlyargs
            .iter()
            .chain(&function.parameters.args)
            .filter(|with_default| {
                !crate::constants::RECEIVER_NAMES.contains(&with_default.parameter.name.id.as_str())
            })
            .count();
        rows.push(FunctionMetricRow {
            line,
            column,
            name: function.name.as_str().to_owned(),
            statement_count: statement_counts[slot],
            distinct_call_count: u32::try_from(call_names[slot].len()).unwrap_or(u32::MAX),
            assigned_local_count: u32::try_from(assigned_names[slot].len()).unwrap_or(u32::MAX),
            parameter_count: u32::try_from(nonreceiver_parameter_names(function).len())
                .unwrap_or(u32::MAX),
            positional_parameter_count: u32::try_from(positional_count).unwrap_or(u32::MAX),
            dunder: is_dunder_name(function.name.as_str()),
        });
    }
    let top_level_slots = top_level_function_slots(module, &nodes, &positions);
    (rows, top_level_slots)
}

fn top_level_function_slots(
    module: &ModModule,
    nodes: &[ShapeNode<'_>],
    positions: &[usize],
) -> Vec<usize> {
    let mut slots: Vec<usize> = Vec::new();
    for statement in &module.body {
        let Stmt::FunctionDef(function) = statement else {
            continue;
        };
        for (slot, position) in positions.iter().enumerate() {
            if function_at(nodes, *position)
                .is_some_and(|candidate| std::ptr::eq(candidate, function))
            {
                slots.push(slot);
                break;
            }
        }
    }
    slots
}
