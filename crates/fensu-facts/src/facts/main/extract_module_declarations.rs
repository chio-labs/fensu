//! Extract module statement shape and classified declarations.

use ruff_python_ast::{ModModule, Stmt};

use crate::facts::_helpers::declarations::rows::{
    collect_alias_rows, collect_class_rows, collect_import_time_calls, collect_statement_rows,
    imported_main_entry_names, main_call_rows, runtime_imported_bindings, static_all_names,
};
use crate::facts::_helpers::naming::names::is_docstring_statement;
use crate::facts::models::ModuleDeclarationRows;
use crate::positions::models::LineIndex;
use crate::syntax::main::breadth_first_nodes::breadth_first_nodes;

/// Return classified module statements and declarations for one module.
pub fn extract_module_declarations(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> ModuleDeclarationRows {
    let breadth_nodes = breadth_first_nodes(module);
    let mut rows = collect_class_rows(
        &breadth_nodes,
        index,
        source,
        ModuleDeclarationRows::default(),
    );
    rows = collect_statement_rows(module, index, source, rows);
    rows = collect_alias_rows(&breadth_nodes, index, source, rows);
    rows.empty_or_docstring_only = module.body.is_empty()
        || (module.body.len() == 1 && is_docstring_statement(&module.body[0]));
    rows.pure_reexport = crate::facts::_helpers::declarations::rows::is_pure_reexport(module);
    rows.top_level_class_count = u32::try_from(
        module
            .body
            .iter()
            .filter(|statement| matches!(statement, Stmt::ClassDef(_)))
            .count(),
    )
    .unwrap_or(u32::MAX);
    rows.static_all_names = static_all_names(module);
    rows.runtime_imported_bindings = runtime_imported_bindings(module);
    let import_time_rows = collect_import_time_calls(module, index, source);
    rows.import_time_call_locations = import_time_rows.import_time_call_locations;
    rows.imported_main_entry_names = imported_main_entry_names(module);
    rows.main_calls = main_call_rows(module, index, source);
    rows
}
