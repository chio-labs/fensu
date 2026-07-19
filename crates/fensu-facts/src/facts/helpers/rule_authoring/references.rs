//! Qualified-reference and assignment-target projections.

use ruff_python_ast::{Expr, ExprContext, Stmt};

use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::models::QualifiedReferenceRow;

pub(crate) fn qualified_reference(expression: &Expr) -> QualifiedReferenceRow {
    let kind = match expression {
        Expr::Name(_) => "name",
        Expr::Attribute(_) => "attribute",
        Expr::Subscript(_) => "subscript",
        _ => "other",
    };
    QualifiedReferenceRow {
        kind: kind.to_owned(),
        name: lenient_reference_name(expression),
        base_name: reference_base_name(expression).map(str::to_owned),
        receiver_base_name: match expression {
            Expr::Attribute(attribute) => reference_base_name(&attribute.value).map(str::to_owned),
            _ => None,
        },
        parts: strict_reference_parts(expression),
    }
}

pub(crate) fn strict_reference_parts(expression: &Expr) -> Vec<String> {
    match expression {
        Expr::Name(name) => vec![name.id.as_str().to_owned()],
        Expr::Attribute(attribute) => {
            let mut parent = strict_reference_parts(&attribute.value);
            if parent.is_empty() {
                Vec::new()
            } else {
                parent.push(attribute.attr.as_str().to_owned());
                parent
            }
        }
        Expr::Subscript(subscript) => strict_reference_parts(&subscript.value),
        _ => Vec::new(),
    }
}

pub(crate) fn stored_target_names(expression: &Expr, names: &mut Vec<String>) {
    match expression {
        Expr::Name(name) if matches!(name.ctx, ExprContext::Store) => {
            names.push(name.id.as_str().to_owned());
        }
        Expr::List(list) => {
            for element in &list.elts {
                stored_target_names(element, names);
            }
        }
        Expr::Tuple(tuple) => {
            for element in &tuple.elts {
                stored_target_names(element, names);
            }
        }
        Expr::Starred(starred) => stored_target_names(&starred.value, names),
        _ => {}
    }
}

pub(crate) fn assignment_parts<'a>(
    node: &'a ShapeNode<'a>,
) -> Option<(Vec<&'a Expr>, Option<&'a Expr>)> {
    match node {
        ShapeNode::Stmt(Stmt::Assign(assignment)) => {
            Some((assignment.targets.iter().collect(), Some(&assignment.value)))
        }
        ShapeNode::Stmt(Stmt::AnnAssign(assignment)) => {
            Some((vec![&assignment.target], assignment.value.as_deref()))
        }
        _ => None,
    }
}

fn lenient_reference_name(expression: &Expr) -> Option<String> {
    match expression {
        Expr::Name(name) => Some(name.id.as_str().to_owned()),
        Expr::Attribute(attribute) => match lenient_reference_name(&attribute.value) {
            Some(parent) => Some(format!("{parent}.{}", attribute.attr)),
            None => Some(attribute.attr.as_str().to_owned()),
        },
        _ => None,
    }
}

fn reference_base_name(expression: &Expr) -> Option<&str> {
    match expression {
        Expr::Name(name) => Some(name.id.as_str()),
        Expr::Attribute(attribute) => Some(attribute.attr.as_str()),
        Expr::Subscript(subscript) => reference_base_name(&subscript.value),
        _ => None,
    }
}
