//! Extract named calls and local call edges.

use ruff_python_ast::{Expr, ModModule, Stmt};

use crate::facts::_helpers::rule_authoring::literals::literal_arguments;
use crate::facts::_helpers::rule_authoring::ownership::{
    ancestor_positions, enclosing_classes, enclosing_functions, function_identity,
    has_loop_ancestor, EnclosingDefinitionsParams,
};
use crate::facts::_helpers::rule_authoring::references::qualified_reference;
use crate::facts::models::{LocalCallEdgeRow, RuleNamedCallRow};
use crate::positions::models::LineIndex;
use crate::syntax::main::breadth_first_with_parents::breadth_first_with_parents;
use crate::syntax::main::start_of::start_of;
use crate::syntax::types::ShapeNode;

/// Return named calls and local edges from independent shared-tree traversals.
pub fn extract_rule_calls(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> (Vec<RuleNamedCallRow>, Vec<LocalCallEdgeRow>) {
    (
        extract_named_calls(module, index, source),
        extract_local_call_edges(module, index, source),
    )
}

fn extract_named_calls(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<RuleNamedCallRow> {
    let (nodes, parents) = breadth_first_with_parents(module);
    let mut rows: Vec<RuleNamedCallRow> = Vec::new();
    for (position, node) in nodes.iter().enumerate() {
        let ShapeNode::Expr(Expr::Call(call)) = node else {
            continue;
        };
        let reference = qualified_reference(&call.func);
        let enclosing_classes = enclosing_classes(EnclosingDefinitionsParams {
            nodes: &nodes,
            parents: &parents,
            position,
            index,
            source,
        });
        let enclosing_functions = enclosing_functions(EnclosingDefinitionsParams {
            nodes: &nodes,
            parents: &parents,
            position,
            index,
            source,
        });
        let (line, column) = start_of(node, index, source);
        let bare_expression = parents[position]
            .is_some_and(|parent| matches!(nodes[parent], ShapeNode::Stmt(Stmt::Expr(_))));
        let super_call = matches!(&*call.func, Expr::Name(name) if name.id.as_str() == "super");
        rows.push(RuleNamedCallRow {
            line,
            column,
            name: reference.name.clone(),
            reference,
            owning_class: enclosing_classes.first().cloned(),
            owning_function: enclosing_functions.first().cloned(),
            enclosing_classes,
            enclosing_functions,
            inside_loop: has_loop_ancestor(&nodes, &parents, position),
            literal_arguments: literal_arguments(call, source),
            bare_expression,
            super_call,
        });
    }
    rows
}

fn extract_local_call_edges(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<LocalCallEdgeRow> {
    let (nodes, parents) = breadth_first_with_parents(module);
    let mut rows: Vec<LocalCallEdgeRow> = Vec::new();
    for (position, node) in nodes.iter().enumerate() {
        let ShapeNode::Expr(Expr::Call(call)) = node else {
            continue;
        };
        let callee = qualified_reference(&call.func);
        let inside_loop = has_loop_ancestor(&nodes, &parents, position);
        let (line, column) = start_of(node, index, source);
        for caller_position in ancestor_positions(&parents, position) {
            let Some(caller) = function_identity(&nodes[caller_position], index, source) else {
                continue;
            };
            let caller_class = enclosing_classes(EnclosingDefinitionsParams {
                nodes: &nodes,
                parents: &parents,
                position: caller_position,
                index,
                source,
            })
            .into_iter()
            .next();
            rows.push(LocalCallEdgeRow {
                line,
                column,
                caller,
                caller_class,
                callee: callee.clone(),
                inside_loop,
            });
        }
    }
    rows
}
