//! Shared name resolution over expressions and statements.

use ruff_python_ast::{Expr, Stmt, StmtClassDef};

use crate::constants;

pub(crate) fn decorator_name(expression: &Expr) -> String {
    match expression {
        Expr::Name(name) => name.id.as_str().to_owned(),
        Expr::Attribute(attribute) => {
            let parent = decorator_name(&attribute.value);
            if parent.is_empty() {
                attribute.attr.as_str().to_owned()
            } else {
                format!("{parent}{}{}", constants::MODULE_SEPARATOR, attribute.attr)
            }
        }
        Expr::Call(call) => decorator_name(&call.func),
        _ => String::new(),
    }
}

pub(crate) fn subscript_base_name(expression: &Expr) -> Option<&str> {
    match expression {
        Expr::Name(name) => Some(name.id.as_str()),
        Expr::Attribute(attribute) => Some(attribute.attr.as_str()),
        Expr::Subscript(subscript) => subscript_base_name(&subscript.value),
        _ => None,
    }
}

pub(crate) fn is_docstring_statement(statement: &Stmt) -> bool {
    match statement {
        Stmt::Expr(inner) => matches!(&*inner.value, Expr::StringLiteral(_)),
        _ => false,
    }
}

pub(crate) fn assignment_target_names(statement: &Stmt) -> Vec<&str> {
    match statement {
        Stmt::Assign(inner) => inner
            .targets
            .iter()
            .filter_map(|target| match target {
                Expr::Name(name) => Some(name.id.as_str()),
                _ => None,
            })
            .collect(),
        Stmt::AnnAssign(inner) => match &*inner.target {
            Expr::Name(name) => vec![name.id.as_str()],
            _ => Vec::new(),
        },
        _ => Vec::new(),
    }
}

pub(crate) fn is_all_assignment(statement: &Stmt) -> bool {
    assignment_target_names(statement).contains(&constants::ALL_EXPORT_NAME)
}

pub(crate) fn is_dataclass_class(class: &ruff_python_ast::StmtClassDef) -> bool {
    class.decorator_list.iter().any(|decorator| {
        decorator_name(&decorator.expression).ends_with(constants::DATACLASS_DECORATOR_NAME)
    })
}

pub(crate) fn class_base_expressions(
    class: &ruff_python_ast::StmtClassDef,
) -> impl Iterator<Item = &Expr> {
    class
        .arguments
        .iter()
        .flat_map(|arguments| arguments.args.iter())
}

pub(crate) fn is_rule_decorated_function(statement: &Stmt) -> bool {
    let Stmt::FunctionDef(function) = statement else {
        return false;
    };
    function.decorator_list.iter().any(|decorator| {
        decorator_name(&decorator.expression)
            .rsplit(constants::MODULE_SEPARATOR)
            .next()
            .is_some_and(|tail| tail == constants::RULE_DECORATOR_NAME)
    })
}

pub(crate) fn is_model_class(class: &StmtClassDef) -> bool {
    if class
        .name
        .as_str()
        .starts_with(constants::PRIVATE_NAME_PREFIX)
    {
        return false;
    }
    is_dataclass_class(class) || has_model_base(class)
}

pub(crate) fn has_model_base(class: &StmtClassDef) -> bool {
    class_base_expressions(class).any(|base| {
        subscript_base_name(base).is_some_and(|name| constants::MODEL_BASE_NAMES.contains(&name))
    })
}

pub(crate) fn is_type_class(class: &StmtClassDef) -> bool {
    if is_dataclass_class(class) || has_model_base(class) {
        return false;
    }
    class_base_expressions(class).any(|base| {
        subscript_base_name(base).is_some_and(|name| constants::TYPE_BASE_NAMES.contains(&name))
    })
}

pub(crate) fn is_exception_class(class: &StmtClassDef) -> bool {
    let name_matches = constants::ERROR_CLASS_SUFFIXES
        .iter()
        .any(|suffix| class.name.as_str().ends_with(suffix));
    name_matches
        || class_base_expressions(class).any(|base| {
            let base_name = subscript_base_name(base).unwrap_or_default();
            constants::ERROR_CLASS_SUFFIXES
                .iter()
                .any(|suffix| base_name.ends_with(suffix))
        })
}

pub(crate) fn is_type_checking_import_block(statement: &Stmt) -> bool {
    let Stmt::If(inner) = statement else {
        return false;
    };
    inner.elif_else_clauses.is_empty()
        && subscript_base_name(&inner.test)
            .is_some_and(|name| name == constants::TYPE_CHECKING_NAME)
        && inner
            .body
            .iter()
            .all(|item| matches!(item, Stmt::Import(_) | Stmt::ImportFrom(_)))
}

pub(crate) fn is_public_type_alias(statement: &Stmt) -> bool {
    match statement {
        Stmt::TypeAlias(inner) => match &*inner.name {
            Expr::Name(name) => !name.id.as_str().starts_with(constants::PRIVATE_NAME_PREFIX),
            _ => false,
        },
        Stmt::AnnAssign(inner) => match &*inner.target {
            Expr::Name(name) => {
                !name.id.as_str().starts_with(constants::PRIVATE_NAME_PREFIX)
                    && subscript_base_name(&inner.annotation)
                        .is_some_and(|base| base == constants::TYPE_ALIAS_NAME)
            }
            _ => false,
        },
        _ => false,
    }
}

pub(crate) fn is_newtype(statement: &Stmt) -> bool {
    let value: Option<&Expr> = match statement {
        Stmt::Assign(inner) => Some(&inner.value),
        Stmt::AnnAssign(inner) => inner.value.as_deref(),
        _ => None,
    };
    let Some(Expr::Call(call)) = value else {
        return false;
    };
    matches!(&*call.func, Expr::Name(_) | Expr::Attribute(_))
        && subscript_base_name(&call.func).is_some_and(|name| name == constants::NEW_TYPE_NAME)
}

pub(crate) fn is_nonexecuting_import_guard(statement: &Stmt) -> bool {
    match statement {
        Stmt::If(inner) => is_nonexecuting_guard(&inner.test),
        _ => false,
    }
}

pub(crate) fn is_nonexecuting_guard(test: &Expr) -> bool {
    if let Expr::Name(name) = test {
        return name.id.as_str() == constants::TYPE_CHECKING_NAME;
    }
    let Expr::Compare(compare) = test else {
        return false;
    };
    if compare.ops.len() != 1 || compare.comparators.len() != 1 {
        return false;
    }
    let left_matches = match &*compare.left {
        Expr::Name(name) => name.id.as_str() == constants::MODULE_NAME_VARIABLE,
        _ => false,
    };
    let comparator_matches = match &compare.comparators[0] {
        Expr::StringLiteral(literal) => literal.value.to_str() == constants::MAIN_MODULE_NAME,
        _ => false,
    };
    left_matches && comparator_matches && matches!(compare.ops[0], ruff_python_ast::CmpOp::Eq)
}
