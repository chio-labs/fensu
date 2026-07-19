//! Resolve discarded project-local calls per top-level function.

use std::collections::HashSet;

use ruff_python_ast::{Expr, ModModule, Stmt, StmtFunctionDef};

use crate::constants;
use crate::facts::helpers::shape::breadth::breadth_first_from;
use crate::facts::helpers::shape::children::children;
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::helpers::state::scopes::argument_names;
use crate::facts::models::DiscardedCallRow;
use crate::positions::models::LineIndex;

pub(crate) fn discarded_call_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<DiscardedCallRow> {
    let mut rows: Vec<DiscardedCallRow> = Vec::new();
    for statement in &module.body {
        let Stmt::FunctionDef(function) = statement else {
            continue;
        };
        let mut shadowed: HashSet<&str> = argument_names(&function.parameters);
        for node in breadth_first_from(ShapeNode::Stmt(statement)) {
            if let ShapeNode::Expr(Expr::Name(name)) = node {
                if matches!(name.ctx, ruff_python_ast::ExprContext::Store) {
                    shadowed.insert(name.id.as_str());
                }
            }
        }
        for body_statement in &function.body {
            collect_bare_calls(
                &ShapeNode::Stmt(body_statement),
                module,
                &shadowed,
                index,
                source,
                &mut rows,
            );
        }
    }
    rows
}

fn collect_bare_calls(
    node: &ShapeNode<'_>,
    module: &ModModule,
    shadowed: &HashSet<&str>,
    index: &LineIndex,
    source: &str,
    rows: &mut Vec<DiscardedCallRow>,
) {
    match node {
        ShapeNode::Stmt(Stmt::FunctionDef(_) | Stmt::ClassDef(_))
        | ShapeNode::Expr(Expr::Lambda(_)) => return,
        ShapeNode::Stmt(Stmt::Expr(inner)) => {
            let call = match &*inner.value {
                Expr::Call(call) => Some(call),
                Expr::Await(awaited) => match &*awaited.value {
                    Expr::Call(call) => Some(call),
                    _ => None,
                },
                _ => None,
            };
            if let Some(call) = call {
                if let Some((module_name, function_name)) = call_target(call, module, shadowed) {
                    let (line, column) = start_of(node, index, source);
                    rows.push(DiscardedCallRow {
                        line,
                        column,
                        module_name,
                        function_name,
                    });
                }
                return;
            }
        }
        _ => {}
    }
    let mut child_buffer: Vec<ShapeNode<'_>> = Vec::new();
    children(node, &mut child_buffer);
    for child in child_buffer {
        collect_bare_calls(&child, module, shadowed, index, source, rows);
    }
}

fn call_target(
    call: &ruff_python_ast::ExprCall,
    module: &ModModule,
    shadowed: &HashSet<&str>,
) -> Option<(Option<String>, String)> {
    match &*call.func {
        Expr::Name(name) => {
            let bare = name.id.as_str();
            if shadowed.contains(bare) {
                return None;
            }
            let local_function = module.body.iter().any(|statement| {
                matches!(statement, Stmt::FunctionDef(inner) if inner.name.as_str() == bare)
            });
            if local_function {
                return Some((None, bare.to_owned()));
            }
            for statement in &module.body {
                let Stmt::ImportFrom(inner) = statement else {
                    continue;
                };
                if inner.level != 0 {
                    continue;
                }
                let Some(module_name) = &inner.module else {
                    continue;
                };
                for alias in &inner.names {
                    let bound = alias
                        .asname
                        .as_ref()
                        .map(|asname| asname.as_str())
                        .unwrap_or_else(|| alias.name.as_str());
                    if bound == bare {
                        return Some((
                            Some(module_name.as_str().to_owned()),
                            alias.name.as_str().to_owned(),
                        ));
                    }
                }
            }
            None
        }
        Expr::Attribute(attribute) => {
            let Expr::Name(value) = &*attribute.value else {
                return None;
            };
            let local_name = value.id.as_str();
            for statement in &module.body {
                let Stmt::Import(inner) = statement else {
                    continue;
                };
                for alias in &inner.names {
                    if alias.asname.is_none()
                        && alias.name.as_str().contains(constants::MODULE_SEPARATOR)
                    {
                        continue;
                    }
                    let bound = alias
                        .asname
                        .as_ref()
                        .map(|asname| asname.as_str())
                        .unwrap_or_else(|| alias.name.as_str());
                    if bound == local_name {
                        return Some((
                            Some(alias.name.as_str().to_owned()),
                            attribute.attr.as_str().to_owned(),
                        ));
                    }
                }
            }
            None
        }
        _ => None,
    }
}

pub(crate) fn project_function_meaningful_result(function: &StmtFunctionDef) -> bool {
    let Some(annotation) = function.returns.as_deref() else {
        return false;
    };
    match annotation {
        Expr::NoneLiteral(_) => false,
        Expr::Name(name) => !constants::NO_RETURN_ANNOTATION_NAMES.contains(&name.id.as_str()),
        Expr::Attribute(attribute) => {
            !constants::NO_RETURN_ANNOTATION_NAMES.contains(&attribute.attr.as_str())
        }
        Expr::StringLiteral(literal) => {
            let tail = literal
                .value
                .to_str()
                .rsplit(constants::MODULE_SEPARATOR)
                .next()
                .unwrap_or_default()
                .to_owned();
            !constants::NO_RETURN_ANNOTATION_NAMES.contains(&tail.as_str())
        }
        _ => true,
    }
}
