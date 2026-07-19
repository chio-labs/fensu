//! Extract top-level class, inheritance, and typed attribute state.

use std::collections::{BTreeMap, BTreeSet};

use ruff_python_ast::{Expr, ExprContext, Stmt, StmtClassDef};

use crate::facts::helpers::shape::children::children;
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::mapping::constants::SELF_RECEIVER_NAME;
use crate::facts::mapping::helpers::expressions::{assigned_names, expression_row};
use crate::facts::mapping::models::{MappingAttributeRow, MappingClassRow};
use crate::positions::models::LineIndex;

pub(crate) fn class_row(class: &StmtClassDef, index: &LineIndex, source: &str) -> MappingClassRow {
    let node = ShapeNode::Stmt(&Stmt::ClassDef(class.clone()));
    let (line, _) = start_of(&node, index, source);
    let bases = class
        .arguments
        .as_ref()
        .map(|arguments| {
            arguments
                .args
                .iter()
                .map(|expression| expression_row(expression, source))
                .collect()
        })
        .unwrap_or_default();
    MappingClassRow {
        name: class.name.as_str().to_owned(),
        line,
        bases,
        class_attributes: class_attributes(class, source),
        instance_attributes: instance_attributes(class, source),
    }
}

fn class_attributes(class: &StmtClassDef, source: &str) -> Vec<MappingAttributeRow> {
    let mut attributes = BTreeMap::new();
    let mut invalid = BTreeSet::new();
    for statement in &class.body {
        if let Stmt::AnnAssign(inner) = statement {
            if let Expr::Name(name) = &*inner.target {
                let name = name.id.as_str().to_owned();
                if !invalid.contains(&name) {
                    attributes.insert(
                        name.clone(),
                        MappingAttributeRow {
                            name,
                            expression: expression_row(&inner.annotation, source),
                            annotation: true,
                        },
                    );
                }
                continue;
            }
        }
        for name in assigned_names(statement) {
            invalid.insert(name.clone());
            attributes.remove(&name);
        }
    }
    attributes.into_values().collect()
}

fn instance_attributes(class: &StmtClassDef, source: &str) -> Vec<MappingAttributeRow> {
    let mut attributes = BTreeMap::new();
    let mut invalid = BTreeSet::new();
    for statement in &class.body {
        let Stmt::FunctionDef(function) = statement else {
            continue;
        };
        for method_statement in &function.body {
            let binding = self_attribute_binding(method_statement, source);
            let targets = self_attribute_targets(method_statement);
            let Some(binding) = binding else {
                for name in targets {
                    invalid.insert(name.clone());
                    attributes.remove(&name);
                }
                continue;
            };
            for name in targets.iter().filter(|name| **name != binding.name) {
                invalid.insert(name.clone());
                attributes.remove(name);
            }
            let incompatible =
                attributes
                    .get(&binding.name)
                    .is_some_and(|previous: &MappingAttributeRow| {
                        previous.annotation != binding.annotation
                            || previous.expression != binding.expression
                    });
            if invalid.contains(&binding.name) || incompatible {
                invalid.insert(binding.name.clone());
                attributes.remove(&binding.name);
            } else {
                attributes.insert(binding.name.clone(), binding);
            }
        }
    }
    attributes.into_values().collect()
}

fn self_attribute_binding(statement: &Stmt, source: &str) -> Option<MappingAttributeRow> {
    match statement {
        Stmt::AnnAssign(inner) => {
            self_attribute_name(&inner.target).map(|name| MappingAttributeRow {
                name: name.to_owned(),
                expression: expression_row(&inner.annotation, source),
                annotation: true,
            })
        }
        Stmt::Assign(inner) if inner.targets.len() == 1 => {
            let name = self_attribute_name(&inner.targets[0])?;
            let Expr::Call(call) = &*inner.value else {
                return None;
            };
            Some(MappingAttributeRow {
                name: name.to_owned(),
                expression: expression_row(&call.func, source),
                annotation: false,
            })
        }
        _ => None,
    }
}

fn self_attribute_targets(statement: &Stmt) -> BTreeSet<String> {
    let mut names = BTreeSet::new();
    collect_self_attribute_targets(ShapeNode::Stmt(statement), &mut names);
    names
}

fn collect_self_attribute_targets(node: ShapeNode<'_>, names: &mut BTreeSet<String>) {
    if matches!(
        node,
        ShapeNode::Stmt(Stmt::FunctionDef(_) | Stmt::ClassDef(_))
            | ShapeNode::Expr(Expr::Lambda(_))
    ) {
        return;
    }
    if let ShapeNode::Expr(expression) = node {
        if let Some(name) = self_attribute_name(expression) {
            if matches!(expression, Expr::Attribute(attribute) if matches!(attribute.ctx, ExprContext::Store | ExprContext::Del))
            {
                names.insert(name.to_owned());
            }
        }
    }
    let mut child_buffer = Vec::new();
    children(&node, &mut child_buffer);
    for child in child_buffer {
        collect_self_attribute_targets(child, names);
    }
}

fn self_attribute_name(expression: &Expr) -> Option<&str> {
    let Expr::Attribute(attribute) = expression else {
        return None;
    };
    match &*attribute.value {
        Expr::Name(name) if name.id.as_str() == SELF_RECEIVER_NAME => Some(attribute.attr.as_str()),
        _ => None,
    }
}
