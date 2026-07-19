//! Build reusable test module-shape rows.

use ruff_python_ast::{Expr, ModModule, Stmt};

use crate::constants;
use crate::facts::helpers::naming::names::{is_dataclass_class, is_docstring_statement};
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::TestModuleRows;
use crate::positions::models::LineIndex;

pub(crate) fn test_module_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> TestModuleRows {
    let mut rows = TestModuleRows {
        empty_or_docstring_only: module.body.is_empty()
            || (module.body.len() == 1 && is_docstring_statement(&module.body[0])),
        ..TestModuleRows::default()
    };
    let mut found_test_function = false;
    for statement in &module.body {
        let location = start_of(&ShapeNode::Stmt(statement), index, source);
        let import_statement = matches!(statement, Stmt::Import(_) | Stmt::ImportFrom(_));
        if !is_docstring_statement(statement) && !import_statement {
            let dataclass = match statement {
                Stmt::ClassDef(class) => is_dataclass_class(class),
                _ => false,
            };
            if !dataclass {
                rows.scenario_invalid.push(location);
            }
        }
        if let Stmt::FunctionDef(function) = statement {
            if function
                .name
                .as_str()
                .starts_with(constants::TEST_FUNCTION_PREFIX)
            {
                found_test_function = true;
            } else {
                rows.top_level_helpers.push(location);
            }
        }
        if is_test_case_list_assignment(statement) {
            rows.test_case_lists.push(location);
        }
        if found_test_function && is_private_assignment(statement) {
            rows.private_after_test.push(location);
        }
    }
    rows
}

fn is_test_case_list_assignment(statement: &Stmt) -> bool {
    match statement {
        Stmt::AnnAssign(inner) => match &*inner.target {
            Expr::Name(name) => is_case_list_name(name.id.as_str()),
            _ => false,
        },
        Stmt::Assign(inner) => inner.targets.iter().any(|target| match target {
            Expr::Name(name) => is_case_list_name(name.id.as_str()),
            _ => false,
        }),
        _ => false,
    }
}

fn is_case_list_name(name: &str) -> bool {
    name == constants::TEST_CASE_LIST_NAME || name.ends_with(constants::TEST_CASE_LIST_SUFFIX)
}

fn is_private_assignment(statement: &Stmt) -> bool {
    match statement {
        Stmt::AnnAssign(inner) => match &*inner.target {
            Expr::Name(name) => name.id.as_str().starts_with(constants::PRIVATE_NAME_PREFIX),
            _ => false,
        },
        Stmt::Assign(inner) => inner.targets.iter().any(|target| match target {
            Expr::Name(name) => name.id.as_str().starts_with(constants::PRIVATE_NAME_PREFIX),
            _ => false,
        }),
        _ => false,
    }
}
