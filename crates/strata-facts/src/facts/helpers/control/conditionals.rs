//! Build conditional and comprehension control-flow rows.

use std::collections::BTreeMap;

use ruff_python_ast::{Expr, ModModule, Stmt};
use ruff_text_size::{Ranged, TextRange};

use crate::facts::helpers::naming::names::decorator_name;
use crate::facts::helpers::shape::breadth::{breadth_first_from, breadth_first_nodes};
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::{span, start_of};
use crate::facts::models::{FunctionConditionalRow, SourceRangeRow};
use crate::positions::models::LineIndex;

pub(crate) fn function_conditional_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<FunctionConditionalRow> {
    let nodes = breadth_first_nodes(module);
    let mut rows: Vec<FunctionConditionalRow> = Vec::new();
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
            let decorator_names: Vec<String> = function
                .decorator_list
                .iter()
                .map(|decorator| decorator_name(&decorator.expression))
                .collect();
            for descendant in breadth_first_from(*node) {
                match &descendant {
                    ShapeNode::Stmt(Stmt::If(_) | Stmt::While(_) | Stmt::Match(_))
                    | ShapeNode::IfTail(_)
                    | ShapeNode::Expr(Expr::If(_)) => {
                        rows.push(conditional_row(
                            function.name.as_str(),
                            &decorator_names,
                            &descendant,
                            index,
                            source,
                        ));
                    }
                    ShapeNode::Comprehension(comprehension) => {
                        for condition in &comprehension.ifs {
                            rows.push(conditional_row(
                                function.name.as_str(),
                                &decorator_names,
                                &ShapeNode::Expr(condition),
                                index,
                                source,
                            ));
                        }
                    }
                    _ => {}
                }
            }
        }
    }
    rows
}

fn conditional_row(
    function_name: &str,
    decorator_names: &[String],
    node: &ShapeNode<'_>,
    index: &LineIndex,
    source: &str,
) -> FunctionConditionalRow {
    FunctionConditionalRow {
        function_name: function_name.to_owned(),
        decorator_names: decorator_names.to_vec(),
        range: range_row(node, index, source),
    }
}

pub(crate) fn range_row(node: &ShapeNode<'_>, index: &LineIndex, source: &str) -> SourceRangeRow {
    let Some((start_line, start_column, end_line, end_column)) = span(node, index, source) else {
        return SourceRangeRow {
            start_line: 1,
            start_column: 0,
            start_offset: 0,
            end_line: 1,
            end_column: 0,
            end_offset: 0,
        };
    };
    let (start_offset, end_offset) = node_offsets(node);
    SourceRangeRow {
        start_line,
        start_column,
        start_offset,
        end_line,
        end_column,
        end_offset,
    }
}

fn node_offsets(node: &ShapeNode<'_>) -> (u32, u32) {
    let range: Option<TextRange> = match node {
        ShapeNode::Stmt(statement) => Some(statement.range()),
        ShapeNode::IfTail(clauses) => match (clauses.first(), clauses.last()) {
            (Some(first), Some(last)) => {
                Some(TextRange::new(first.range().start(), last.range().end()))
            }
            _ => None,
        },
        ShapeNode::Expr(expression) => Some(expression.range()),
        _ => None,
    };
    match range {
        Some(inner) => (
            u32::try_from(inner.start().to_usize()).unwrap_or(u32::MAX),
            u32::try_from(inner.end().to_usize()).unwrap_or(u32::MAX),
        ),
        None => (0, 0),
    }
}

pub(crate) fn complex_comprehension_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<(u32, u32)> {
    let nodes = breadth_first_nodes(module);
    let matchers: [fn(&ShapeNode<'_>) -> bool; 4] = [
        |node| matches!(node, ShapeNode::Expr(Expr::ListComp(_))),
        |node| matches!(node, ShapeNode::Expr(Expr::SetComp(_))),
        |node| matches!(node, ShapeNode::Expr(Expr::DictComp(_))),
        |node| {
            matches!(node, ShapeNode::Expr(Expr::Generator(_)))
                || matches!(node, ShapeNode::GeneratorInCall(_, _))
        },
    ];
    let mut rows: Vec<(u32, u32)> = Vec::new();
    for matcher in matchers {
        for node in &nodes {
            if matcher(node) && is_complex_comprehension(node) {
                rows.push(start_of(node, index, source));
            }
        }
    }
    rows
}

pub(crate) fn is_complex_comprehension(node: &ShapeNode<'_>) -> bool {
    generator_count(node) > 1 || contains_nested_comprehension(node)
}

fn generator_count(node: &ShapeNode<'_>) -> usize {
    match node {
        ShapeNode::Expr(Expr::ListComp(inner)) => inner.generators.len(),
        ShapeNode::Expr(Expr::SetComp(inner)) => inner.generators.len(),
        ShapeNode::Expr(Expr::DictComp(inner)) => inner.generators.len(),
        ShapeNode::Expr(Expr::Generator(inner)) => inner.generators.len(),
        ShapeNode::GeneratorInCall(inner, _) => inner.generators.len(),
        _ => 0,
    }
}

fn contains_nested_comprehension(node: &ShapeNode<'_>) -> bool {
    let mut child_buffer: Vec<ShapeNode<'_>> = Vec::new();
    crate::facts::helpers::shape::children::children(node, &mut child_buffer);
    for child in child_buffer {
        for descendant in breadth_first_from(child) {
            if is_comprehension(&descendant) {
                return true;
            }
        }
    }
    false
}

fn is_comprehension(node: &ShapeNode<'_>) -> bool {
    matches!(
        node,
        ShapeNode::Expr(
            Expr::ListComp(_) | Expr::SetComp(_) | Expr::DictComp(_) | Expr::Generator(_)
        ) | ShapeNode::GeneratorInCall(_, _)
    )
}

pub(crate) fn test_conditional_rows(
    definitions: &[&Stmt],
    index: &LineIndex,
    source: &str,
) -> Vec<(u32, u32)> {
    let mut by_position: BTreeMap<(u32, u32), (u32, u32)> = BTreeMap::new();
    for definition in definitions {
        let body: &[Stmt] = match definition {
            Stmt::FunctionDef(inner) => &inner.body,
            Stmt::ClassDef(inner) => &inner.body,
            _ => continue,
        };
        for statement in body {
            for node in breadth_first_from(ShapeNode::Stmt(statement)) {
                let conditional = matches!(
                    &node,
                    ShapeNode::Stmt(Stmt::If(_) | Stmt::Match(_))
                        | ShapeNode::IfTail(_)
                        | ShapeNode::Expr(Expr::If(_))
                );
                let filtered_comprehension = is_comprehension(&node)
                    && has_comprehension_filter(&node)
                    && !is_complex_comprehension(&node);
                if conditional || filtered_comprehension {
                    let location = start_of(&node, index, source);
                    by_position.insert(location, location);
                }
            }
        }
    }
    by_position.into_values().collect()
}

fn has_comprehension_filter(node: &ShapeNode<'_>) -> bool {
    let generators = match node {
        ShapeNode::Expr(Expr::ListComp(inner)) => &inner.generators,
        ShapeNode::Expr(Expr::SetComp(inner)) => &inner.generators,
        ShapeNode::Expr(Expr::DictComp(inner)) => &inner.generators,
        ShapeNode::Expr(Expr::Generator(inner)) => &inner.generators,
        ShapeNode::GeneratorInCall(inner, _) => &inner.generators,
        _ => return false,
    };
    generators.iter().any(|generator| !generator.ifs.is_empty())
}
