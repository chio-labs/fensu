//! Deterministic recognition of root-level public API facades.

use std::collections::{HashMap, HashSet};

use ruff_python_ast::{Expr, ModModule, Stmt, StmtClassDef, StmtFunctionDef};

use crate::mapping::main::extract_runtime_imports::extract_runtime_imports;
use crate::syntax::main::breadth_first_from::breadth_first_from;
use crate::syntax::types::ShapeNode;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ImportedKind {
    ContextManager,
    Overload,
    Other,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ImportedBinding {
    internal: bool,
    kind: ImportedKind,
}

/// Return whether one module is a statically bounded public API facade.
pub(crate) fn is_public_facade(module: &ModModule, package_name: &str) -> bool {
    let Some(exports) = static_exports(module) else {
        return false;
    };
    if exports.is_empty() {
        return false;
    }
    let imports = imported_bindings(module, package_name);
    let local_declarations = module
        .body
        .iter()
        .filter_map(|statement| match statement {
            Stmt::FunctionDef(function) => Some(function.name.as_str().to_owned()),
            Stmt::ClassDef(class) => Some(class.name.as_str().to_owned()),
            _ => None,
        })
        .collect::<HashSet<_>>();
    let mut supported: HashSet<String> = imports
        .iter()
        .filter_map(|(name, binding)| binding.internal.then_some(name.clone()))
        .collect();

    for statement in &module.body {
        match statement {
            Stmt::Expr(_) if is_docstring_statement(statement) => {}
            Stmt::Import(_) | Stmt::ImportFrom(_) => {}
            Stmt::Assign(_) if is_all_assignment(statement) => {}
            Stmt::AnnAssign(assignment) if is_all_assignment(statement) => {
                if contains_call(&assignment.annotation) {
                    return false;
                }
            }
            Stmt::FunctionDef(function) => {
                if !exports.contains(function.name.as_str()) {
                    return false;
                }
                if function_has_import_time_behavior(function) {
                    return false;
                }
                if overload_stub(function, without_docstring(&function.body), &imports) {
                    continue;
                }
                let Some(internal) = facade_function(function, &imports, &local_declarations)
                else {
                    return false;
                };
                if !internal {
                    return false;
                }
                supported.insert(function.name.as_str().to_owned());
            }
            Stmt::ClassDef(class) => {
                if !exports.contains(class.name.as_str()) {
                    return false;
                }
                let Some(internal) = facade_class(class, &imports) else {
                    return false;
                };
                if !internal {
                    return false;
                }
                supported.insert(class.name.as_str().to_owned());
            }
            Stmt::Assign(assignment) => {
                let [Expr::Name(target)] = assignment.targets.as_slice() else {
                    return false;
                };
                let Expr::Name(value) = &*assignment.value else {
                    return false;
                };
                if !exports.contains(target.id.as_str()) {
                    return false;
                }
                let Some(binding) = imports.get(value.id.as_str()) else {
                    return false;
                };
                if !binding.internal {
                    return false;
                }
                supported.insert(target.id.as_str().to_owned());
            }
            Stmt::AnnAssign(assignment) => {
                let (Expr::Name(target), Some(value)) = (&*assignment.target, &assignment.value)
                else {
                    return false;
                };
                if contains_call(&assignment.annotation) {
                    return false;
                }
                let Expr::Name(value) = &**value else {
                    return false;
                };
                if !exports.contains(target.id.as_str()) {
                    return false;
                }
                let Some(binding) = imports.get(value.id.as_str()) else {
                    return false;
                };
                if !binding.internal {
                    return false;
                }
                supported.insert(target.id.as_str().to_owned());
            }
            _ => return false,
        }
    }

    exports.iter().all(|name| supported.contains(name))
}

fn static_exports(module: &ModModule) -> Option<HashSet<String>> {
    let assignments = module
        .body
        .iter()
        .filter(|statement| is_all_assignment(statement))
        .collect::<Vec<_>>();
    let [statement] = assignments.as_slice() else {
        return None;
    };
    let value = match statement {
        Stmt::Assign(assignment) => &*assignment.value,
        Stmt::AnnAssign(assignment) => assignment.value.as_deref()?,
        _ => return None,
    };
    let items = match value {
        Expr::List(value) => value.elts.as_slice(),
        Expr::Tuple(value) => value.elts.as_slice(),
        _ => return None,
    };
    let names = items
        .iter()
        .map(|item| match item {
            Expr::StringLiteral(value) => Some(value.value.to_str().to_owned()),
            _ => None,
        })
        .collect::<Option<Vec<_>>>()?;
    (names.len() == names.iter().collect::<HashSet<_>>().len()).then(|| names.into_iter().collect())
}

fn imported_bindings(module: &ModModule, package_name: &str) -> HashMap<String, ImportedBinding> {
    let mut bindings: HashMap<String, ImportedBinding> = HashMap::new();
    for row in extract_runtime_imports(module) {
        if row.module.as_deref() == Some("__future__") {
            continue;
        }
        let internal_module = row.level > 0
            || row.module.as_deref().is_some_and(|name| {
                name == package_name || name.starts_with(&format!("{package_name}."))
            });
        for alias in row.aliases {
            let internal = internal_module
                || (!row.from_import
                    && (alias.name == package_name
                        || alias.name.starts_with(&format!("{package_name}."))));
            let bound_name = alias.asname.clone().unwrap_or_else(|| {
                if row.from_import {
                    alias.name.clone()
                } else {
                    alias.name.split('.').next().unwrap_or_default().to_owned()
                }
            });
            let kind = match (row.module.as_deref(), alias.name.as_str()) {
                (Some("contextlib"), "contextmanager" | "asynccontextmanager") => {
                    ImportedKind::ContextManager
                }
                (Some("typing"), "overload") => ImportedKind::Overload,
                _ => ImportedKind::Other,
            };
            bindings.insert(bound_name, ImportedBinding { internal, kind });
        }
    }
    bindings
}

fn facade_function(
    function: &StmtFunctionDef,
    imports: &HashMap<String, ImportedBinding>,
    local_declarations: &HashSet<String>,
) -> Option<bool> {
    if function_has_import_time_behavior(function) {
        return None;
    }
    let body = without_docstring(&function.body);
    if context_manager_wrapper(function, body, imports, local_declarations) {
        return body.first().and_then(|statement| match statement {
            Stmt::With(statement) => statement
                .items
                .first()
                .and_then(|item| imported_call_binding(&item.context_expr, imports))
                .map(|binding| binding.internal),
            _ => None,
        });
    }
    if !function.decorator_list.is_empty() || body.len() != 1 {
        return None;
    }
    let expression = match &body[0] {
        Stmt::Return(statement) => statement.value.as_deref()?,
        Stmt::Expr(statement) => &*statement.value,
        Stmt::Assign(statement) if matches!(statement.targets.as_slice(), [Expr::Name(name)] if name.id.as_str() == "_") => {
            &statement.value
        }
        _ => return None,
    };
    if function_shadows_call(function, expression, local_declarations) {
        return None;
    }
    imported_call_binding(expression, imports).map(|binding| binding.internal)
}

fn overload_stub(
    function: &StmtFunctionDef,
    body: &[Stmt],
    imports: &HashMap<String, ImportedBinding>,
) -> bool {
    function.decorator_list.len() == 1
        && decorator_kind(function, imports) == Some(ImportedKind::Overload)
        && matches!(body, [Stmt::Expr(statement)] if matches!(&*statement.value, Expr::EllipsisLiteral(_)))
}

fn context_manager_wrapper(
    function: &StmtFunctionDef,
    body: &[Stmt],
    imports: &HashMap<String, ImportedBinding>,
    local_declarations: &HashSet<String>,
) -> bool {
    if function.decorator_list.len() != 1
        || decorator_kind(function, imports) != Some(ImportedKind::ContextManager)
    {
        return false;
    }
    let [Stmt::With(statement)] = body else {
        return false;
    };
    let [item] = statement.items.as_slice() else {
        return false;
    };
    if imported_call_binding(&item.context_expr, imports).is_none()
        || function_shadows_call(function, &item.context_expr, local_declarations)
    {
        return false;
    }
    let [Stmt::Expr(yield_statement)] = statement.body.as_slice() else {
        return false;
    };
    let Expr::Yield(yielded) = &*yield_statement.value else {
        return false;
    };
    match (item.optional_vars.as_deref(), yielded.value.as_deref()) {
        (None, None) => true,
        (Some(Expr::Name(bound)), Some(Expr::Name(value))) => bound.id == value.id,
        _ => false,
    }
}

fn function_has_import_time_behavior(function: &StmtFunctionDef) -> bool {
    function
        .parameters
        .iter()
        .filter_map(|parameter| parameter.annotation())
        .chain(function.returns.as_deref())
        .any(contains_call)
        || function
            .parameters
            .iter_non_variadic_params()
            .filter_map(|parameter| parameter.default())
            .any(|value| contains_call(value) || mutable_literal(value))
}

fn function_shadows_call(
    function: &StmtFunctionDef,
    expression: &Expr,
    local_declarations: &HashSet<String>,
) -> bool {
    let Some(root) = call_root(expression) else {
        return false;
    };
    local_declarations.contains(root)
        || function
            .parameters
            .iter()
            .any(|parameter| parameter.name().as_str() == root)
}

fn call_root(expression: &Expr) -> Option<&str> {
    let call = match expression {
        Expr::Call(call) => call,
        Expr::Await(value) => match &*value.value {
            Expr::Call(call) => call,
            _ => return None,
        },
        _ => return None,
    };
    expression_root(&call.func)
}

fn expression_root(expression: &Expr) -> Option<&str> {
    match expression {
        Expr::Name(name) => Some(name.id.as_str()),
        Expr::Attribute(attribute) => expression_root(&attribute.value),
        _ => None,
    }
}

fn decorator_kind(
    function: &StmtFunctionDef,
    imports: &HashMap<String, ImportedBinding>,
) -> Option<ImportedKind> {
    let decorator = function.decorator_list.first()?;
    let Expr::Name(name) = &decorator.expression else {
        return None;
    };
    imports.get(name.id.as_str()).map(|binding| binding.kind)
}

fn facade_class(class: &StmtClassDef, imports: &HashMap<String, ImportedBinding>) -> Option<bool> {
    if !class.decorator_list.is_empty() {
        return None;
    }
    let arguments = class.arguments.as_ref()?;
    let [base] = arguments.args.as_ref() else {
        return None;
    };
    if !arguments.keywords.is_empty()
        || without_docstring(&class.body)
            .iter()
            .any(|statement| !matches!(statement, Stmt::Pass(_)))
    {
        return None;
    }
    imported_expression_binding(base, imports).map(|binding| binding.internal)
}

fn imported_call_binding<'a>(
    expression: &Expr,
    imports: &'a HashMap<String, ImportedBinding>,
) -> Option<&'a ImportedBinding> {
    let call = match expression {
        Expr::Call(call) => call,
        Expr::Await(value) => match &*value.value {
            Expr::Call(call) => call,
            _ => return None,
        },
        _ => return None,
    };
    if call
        .arguments
        .args
        .iter()
        .any(|argument| !forwarded_value(argument))
        || call
            .arguments
            .keywords
            .iter()
            .any(|keyword| !forwarded_value(&keyword.value))
    {
        return None;
    }
    imported_expression_binding(&call.func, imports)
}

fn imported_expression_binding<'a>(
    expression: &Expr,
    imports: &'a HashMap<String, ImportedBinding>,
) -> Option<&'a ImportedBinding> {
    let root = match expression {
        Expr::Name(name) => name.id.as_str(),
        Expr::Attribute(attribute) => {
            return imported_expression_binding(&attribute.value, imports)
        }
        _ => return None,
    };
    imports.get(root)
}

fn forwarded_value(expression: &Expr) -> bool {
    match expression {
        Expr::Name(_)
        | Expr::StringLiteral(_)
        | Expr::BytesLiteral(_)
        | Expr::NumberLiteral(_)
        | Expr::BooleanLiteral(_)
        | Expr::NoneLiteral(_) => true,
        Expr::Attribute(attribute) => forwarded_value(&attribute.value),
        Expr::Starred(starred) => forwarded_value(&starred.value),
        Expr::List(list) => list.elts.iter().all(forwarded_value),
        Expr::Tuple(tuple) => tuple.elts.iter().all(forwarded_value),
        _ => false,
    }
}

fn contains_call(expression: &Expr) -> bool {
    breadth_first_from(ShapeNode::Expr(expression))
        .iter()
        .any(|node| matches!(node, ShapeNode::Expr(Expr::Call(_))))
}

fn mutable_literal(expression: &Expr) -> bool {
    matches!(expression, Expr::Dict(_) | Expr::List(_) | Expr::Set(_))
}

fn without_docstring(body: &[Stmt]) -> &[Stmt] {
    if body.first().is_some_and(is_docstring_statement) {
        &body[1..]
    } else {
        body
    }
}

fn is_all_assignment(statement: &Stmt) -> bool {
    match statement {
        Stmt::Assign(assignment) => assignment
            .targets
            .iter()
            .any(|target| matches!(target, Expr::Name(name) if name.id.as_str() == "__all__")),
        Stmt::AnnAssign(assignment) => {
            matches!(&*assignment.target, Expr::Name(name) if name.id.as_str() == "__all__")
        }
        _ => false,
    }
}

fn is_docstring_statement(statement: &Stmt) -> bool {
    matches!(statement, Stmt::Expr(inner) if matches!(&*inner.value, Expr::StringLiteral(_)))
}
