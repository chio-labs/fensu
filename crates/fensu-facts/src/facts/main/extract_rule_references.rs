//! Extract assignment and comparison reference facts.

use ruff_python_ast::{Expr, ModModule};

use crate::facts::helpers::rule_authoring::ownership::{enclosing_classes, enclosing_functions};
use crate::facts::helpers::rule_authoring::references::{
    assignment_parts, qualified_reference, stored_target_names, strict_reference_parts,
};
use crate::facts::helpers::shape::breadth::{breadth_first_nodes, breadth_first_with_parents};
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::{AssignmentReferenceRow, ComparisonRow};
use crate::positions::models::LineIndex;

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
    let mut rows = Vec::new();
    for (position, node) in nodes.iter().enumerate() {
        let Some((targets, value)) = assignment_parts(node) else {
            continue;
        };
        let mut target_names = Vec::new();
        for target in targets {
            stored_target_names(target, &mut target_names);
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
        let classes = enclosing_classes(&nodes, &parents, position, index, source);
        let functions = enclosing_functions(&nodes, &parents, position, index, source);
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
    let mut rows = Vec::new();
    for node in breadth_first_nodes(module) {
        let ShapeNode::Expr(Expr::Compare(compare)) = node else {
            continue;
        };
        let operands = std::iter::once(&*compare.left).chain(compare.comparators.iter());
        let operand_references = operands
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
