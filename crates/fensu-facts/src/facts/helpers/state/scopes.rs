//! Lexical scope metadata for outer-state resolution.

use std::collections::{HashSet, VecDeque};

use ruff_python_ast::{Expr, ExprContext, Stmt, StmtFunctionDef};

use crate::constants;
use crate::facts::helpers::shape::children::children;
use crate::facts::helpers::shape::nodes::ShapeNode;

pub(crate) struct ScopeMetadata<'a> {
    pub(crate) bindings: HashSet<&'a str>,
    pub(crate) global_names: HashSet<&'a str>,
    pub(crate) nonlocal_names: HashSet<&'a str>,
}

pub(crate) fn scope_metadata<'a>(
    statements: &'a [Stmt],
    include_imports: bool,
) -> ScopeMetadata<'a> {
    let mut metadata = ScopeMetadata {
        bindings: HashSet::new(),
        global_names: HashSet::new(),
        nonlocal_names: HashSet::new(),
    };
    let mut pending: VecDeque<ShapeNode<'a>> = statements.iter().map(ShapeNode::Stmt).collect();
    let mut child_buffer: Vec<ShapeNode<'a>> = Vec::new();
    while let Some(node) = pending.pop_front() {
        match &node {
            ShapeNode::Stmt(Stmt::FunctionDef(inner)) => {
                metadata.bindings.insert(inner.name.as_str());
                continue;
            }
            ShapeNode::Stmt(Stmt::ClassDef(inner)) => {
                metadata.bindings.insert(inner.name.as_str());
                continue;
            }
            ShapeNode::Expr(
                Expr::Lambda(_)
                | Expr::ListComp(_)
                | Expr::SetComp(_)
                | Expr::DictComp(_)
                | Expr::Generator(_),
            )
            | ShapeNode::GeneratorInCall(_, _) => continue,
            ShapeNode::Stmt(Stmt::Global(inner)) => {
                for name in &inner.names {
                    metadata.global_names.insert(name.as_str());
                }
            }
            ShapeNode::Stmt(Stmt::Nonlocal(inner)) => {
                for name in &inner.names {
                    metadata.nonlocal_names.insert(name.as_str());
                }
            }
            ShapeNode::Stmt(Stmt::Import(inner)) if include_imports => {
                for alias in &inner.names {
                    let bound = match &alias.asname {
                        Some(asname) => asname.as_str(),
                        None => alias
                            .name
                            .as_str()
                            .split(constants::MODULE_SEPARATOR)
                            .next()
                            .unwrap_or_default(),
                    };
                    metadata.bindings.insert(bound);
                }
            }
            ShapeNode::Stmt(Stmt::ImportFrom(inner)) if include_imports => {
                for alias in &inner.names {
                    if alias.name.as_str() == constants::WILDCARD_IMPORT_NAME {
                        continue;
                    }
                    let bound = match &alias.asname {
                        Some(asname) => asname.as_str(),
                        None => alias.name.as_str(),
                    };
                    metadata.bindings.insert(bound);
                }
            }
            ShapeNode::ExceptHandler(handler) => {
                if let Some(name) = &handler.name {
                    metadata.bindings.insert(name.as_str());
                }
            }
            ShapeNode::Expr(Expr::Name(name)) => {
                if matches!(name.ctx, ExprContext::Store | ExprContext::Del) {
                    metadata.bindings.insert(name.id.as_str());
                }
            }
            _ => {}
        }
        child_buffer.clear();
        children(&node, &mut child_buffer);
        for child in &child_buffer {
            pending.push_back(*child);
        }
    }
    metadata
}

pub(crate) fn argument_names(function_parameters: &ruff_python_ast::Parameters) -> HashSet<&str> {
    let mut names: HashSet<&str> = HashSet::new();
    for with_default in function_parameters
        .posonlyargs
        .iter()
        .chain(&function_parameters.args)
        .chain(&function_parameters.kwonlyargs)
    {
        names.insert(with_default.parameter.name.id.as_str());
    }
    if let Some(vararg) = &function_parameters.vararg {
        names.insert(vararg.name.id.as_str());
    }
    if let Some(kwarg) = &function_parameters.kwarg {
        names.insert(kwarg.name.id.as_str());
    }
    names
}

pub(crate) fn function_local_bindings<'a>(function: &'a StmtFunctionDef) -> ScopeMetadata<'a> {
    let inner = scope_metadata(&function.body, true);
    let mut bindings: HashSet<&'a str> = argument_names(&function.parameters);
    bindings.extend(&inner.bindings);
    for name in &inner.global_names {
        bindings.remove(name);
    }
    for name in &inner.nonlocal_names {
        bindings.remove(name);
    }
    ScopeMetadata {
        bindings,
        global_names: inner.global_names,
        nonlocal_names: inner.nonlocal_names,
    }
}
