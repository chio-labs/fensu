//! Build import and attribute-reference rows in breadth-first order.

use std::collections::HashMap;

use ruff_python_ast::{Expr, ModModule, Stmt};

use crate::constants;
use crate::facts::helpers::shape::breadth::breadth_first_nodes;
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::{ImportAliasRow, ImportRow, ReferenceEventRow, ReferenceRows};
use crate::positions::models::LineIndex;

pub(crate) fn reference_rows(module: &ModModule, index: &LineIndex, source: &str) -> ReferenceRows {
    let nodes = breadth_first_nodes(module);
    let mut rows = ReferenceRows::default();
    let mut import_slot_by_position: HashMap<usize, usize> = HashMap::new();
    for from_import in [true, false] {
        for (position, node) in nodes.iter().enumerate() {
            let ShapeNode::Stmt(statement) = node else {
                continue;
            };
            let matches_kind = match statement {
                Stmt::ImportFrom(_) => from_import,
                Stmt::Import(_) => !from_import,
                _ => continue,
            };
            if !matches_kind {
                continue;
            }
            let top_level = module
                .body
                .iter()
                .any(|candidate| std::ptr::eq(candidate, *statement));
            let (line, column) = start_of(node, index, source);
            import_slot_by_position.insert(position, rows.imports.len());
            rows.imports
                .push(import_row(statement, line, column, top_level));
        }
    }
    for (position, node) in nodes.iter().enumerate() {
        if let Some(slot) = import_slot_by_position.get(&position) {
            rows.events.push(ReferenceEventRow::Import(*slot));
            continue;
        }
        let ShapeNode::Expr(Expr::Attribute(attribute)) = node else {
            continue;
        };
        if !is_private_class_name(attribute.attr.as_str()) {
            continue;
        }
        let (line, column) = start_of(node, index, source);
        rows.events.push(ReferenceEventRow::Attribute {
            line,
            column,
            base_name: attribute_base_name(&attribute.value).map(str::to_owned),
            attribute_name: attribute.attr.as_str().to_owned(),
        });
    }
    rows
}

fn import_row(statement: &Stmt, line: u32, column: u32, top_level: bool) -> ImportRow {
    match statement {
        Stmt::ImportFrom(inner) => ImportRow {
            line,
            column,
            module_parts: inner
                .module
                .as_ref()
                .map(|name| {
                    name.as_str()
                        .split(constants::MODULE_SEPARATOR)
                        .map(str::to_owned)
                        .collect()
                })
                .unwrap_or_default(),
            aliases: inner
                .names
                .iter()
                .map(|alias| ImportAliasRow {
                    imported_name: alias.name.as_str().to_owned(),
                    bound_name: alias
                        .asname
                        .as_ref()
                        .map(|asname| asname.as_str())
                        .unwrap_or_else(|| {
                            alias
                                .name
                                .as_str()
                                .rsplit(constants::MODULE_SEPARATOR)
                                .next()
                                .unwrap_or_default()
                        })
                        .to_owned(),
                })
                .collect(),
            relative_level: inner.level,
            from_import: true,
            top_level,
        },
        Stmt::Import(inner) => ImportRow {
            line,
            column,
            module_parts: Vec::new(),
            aliases: inner
                .names
                .iter()
                .map(|alias| ImportAliasRow {
                    imported_name: alias.name.as_str().to_owned(),
                    bound_name: alias
                        .asname
                        .as_ref()
                        .map(|asname| asname.as_str())
                        .unwrap_or_else(|| {
                            alias
                                .name
                                .as_str()
                                .rsplit(constants::MODULE_SEPARATOR)
                                .next()
                                .unwrap_or_default()
                        })
                        .to_owned(),
                })
                .collect(),
            relative_level: 0,
            from_import: false,
            top_level,
        },
        _ => ImportRow {
            line,
            column,
            module_parts: Vec::new(),
            aliases: Vec::new(),
            relative_level: 0,
            from_import: false,
            top_level,
        },
    }
}

pub(crate) fn attribute_base_name(expression: &Expr) -> Option<&str> {
    match expression {
        Expr::Name(name) => Some(name.id.as_str()),
        Expr::Attribute(attribute) => attribute_base_name(&attribute.value),
        _ => None,
    }
}

fn is_private_class_name(name: &str) -> bool {
    let mut characters = name.chars();
    let Some(first) = characters.next() else {
        return false;
    };
    let Some(second) = characters.next() else {
        return false;
    };
    first == '_' && second.is_uppercase()
}
