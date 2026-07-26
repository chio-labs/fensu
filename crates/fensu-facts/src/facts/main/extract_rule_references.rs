//! Extract assignment and comparison reference facts.

use ruff_python_ast::{Expr, ModModule};

use crate::facts::_helpers::rule_authoring::ownership::{
    enclosing_classes, enclosing_functions, EnclosingDefinitionsParams,
};
use crate::facts::_helpers::rule_authoring::references::assignment_parts;
use crate::facts::_helpers::rule_authoring::references::qualified_reference;
use crate::facts::_helpers::rule_authoring::references::stored_target_names;
use crate::facts::models::{AssignmentReferenceRow, ComparisonRow, QualifiedReferenceRow};
use crate::positions::models::LineIndex;
use crate::syntax::main::breadth_first_nodes::breadth_first_nodes;
use crate::syntax::main::breadth_first_with_parents::breadth_first_with_parents;
use crate::syntax::main::start_of::start_of;
use crate::syntax::main::strict_reference_parts::strict_reference_parts;
use crate::syntax::types::ShapeNode;

/// Return assignment and comparison references from independent shared-tree traversals.
pub fn extract_rule_references(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> (Vec<AssignmentReferenceRow>, Vec<ComparisonRow>) {
    (
        extract_assignment_references(module, index, source),
        extract_comparisons(module, index, source),
    )
}

fn extract_assignment_references(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<AssignmentReferenceRow> {
    let (nodes, parents) = breadth_first_with_parents(module);
    let mut rows: Vec<AssignmentReferenceRow> = Vec::new();
    for (position, node) in nodes.iter().enumerate() {
        let Some((targets, value)) = assignment_parts(node) else {
            continue;
        };
        let mut target_names: Vec<String> = Vec::new();
        for target in targets {
            target_names = stored_target_names(target, target_names);
        }
        let value_reference = value.and_then(|expression| {
            if matches!(expression, Expr::Name(_) | Expr::Attribute(_))
                && !strict_reference_parts(expression).is_empty()
            {
                Some(qualified_reference(expression))
            } else {
                None
            }
        });
        let classes = enclosing_classes(EnclosingDefinitionsParams {
            nodes: &nodes,
            parents: &parents,
            position,
            index,
            source,
        });
        let functions = enclosing_functions(EnclosingDefinitionsParams {
            nodes: &nodes,
            parents: &parents,
            position,
            index,
            source,
        });
        let (line, column) = start_of(node, index, source);
        rows.push(AssignmentReferenceRow {
            line,
            column,
            owning_class: classes.into_iter().next(),
            owning_function: functions.into_iter().next(),
            target_names,
            value_reference,
        });
    }
    rows
}

fn extract_comparisons(module: &ModModule, index: &LineIndex, source: &str) -> Vec<ComparisonRow> {
    let mut rows: Vec<ComparisonRow> = Vec::new();
    for node in breadth_first_nodes(module) {
        let ShapeNode::Expr(Expr::Compare(compare)) = node else {
            continue;
        };
        let operands = std::iter::once(&*compare.left).chain(compare.comparators.iter());
        let operand_references: Vec<Option<QualifiedReferenceRow>> = operands
            .map(|operand| match operand {
                Expr::Name(_) | Expr::Attribute(_) | Expr::Subscript(_) => {
                    Some(qualified_reference(operand))
                }
                _ => None,
            })
            .collect();
        let (line, column) = start_of(&node, index, source);
        rows.push(ComparisonRow {
            line,
            column,
            operand_references,
        });
    }
    rows
}
