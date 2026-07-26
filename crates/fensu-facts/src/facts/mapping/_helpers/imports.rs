//! Extract runtime and annotation import views.

use ruff_python_ast::{Expr, ModModule, Stmt};

use crate::facts::mapping::constants::TYPE_CHECKING_NAME;
use crate::facts::mapping::models::{MappingImportAliasRow, MappingImportRow};

pub(crate) fn mapping_imports(
    module: &ModModule,
) -> (Vec<MappingImportRow>, Vec<MappingImportRow>) {
    let mut runtime = Vec::new();
    let mut annotation = Vec::new();
    for statement in &module.body {
        if let Some(row) = import_row(statement) {
            runtime.push(row.clone());
            annotation.push(row);
            continue;
        }
        let Stmt::If(guard) = statement else {
            continue;
        };
        if !is_type_checking_expression(&guard.test) {
            continue;
        }
        for child in &guard.body {
            if let Some(row) = import_row(child) {
                annotation.push(row);
            }
        }
        if let Some(clause) = guard.elif_else_clauses.last() {
            if clause.test.is_none() {
                for child in &clause.body {
                    if let Some(row) = import_row(child) {
                        runtime.push(row);
                    }
                }
            }
        }
    }
    (runtime, annotation)
}

fn is_type_checking_expression(expression: &Expr) -> bool {
    matches!(expression, Expr::Name(name) if name.id.as_str() == TYPE_CHECKING_NAME)
        || matches!(expression, Expr::Attribute(attribute) if attribute.attr.as_str() == TYPE_CHECKING_NAME)
}

fn import_row(statement: &Stmt) -> Option<MappingImportRow> {
    let (module, level, names, from_import) = match statement {
        Stmt::Import(inner) => (None, 0, &inner.names, false),
        Stmt::ImportFrom(inner) => (
            inner.module.as_ref().map(|name| name.as_str().to_owned()),
            inner.level,
            &inner.names,
            true,
        ),
        _ => return None,
    };
    Some(MappingImportRow {
        module,
        level,
        aliases: names
            .iter()
            .map(|alias| MappingImportAliasRow {
                name: alias.name.as_str().to_owned(),
                asname: alias.asname.as_ref().map(|name| name.as_str().to_owned()),
            })
            .collect(),
        from_import,
    })
}
