//! File-local role surface, source-size, and direct-tooling policy.

use strata_facts::extension::models::ProgramHandle;
use strata_facts::facts::models::{ModuleDeclarationRows, ModuleStatementRow};

use crate::rules::constants::{
    CLASSES_ONE_CLASS_PER_MODULE_CODE, ENTRY_MODULE_SHAPE_CODE, INIT_MODULE_EMPTY_CODE,
    NO_REEXPORT_SHIM_CODE, PUBLIC_SURFACE_SHAPE_CODE, SOURCE_FILE_LINE_COUNT_CODE,
    TOOLING_ENTRYPOINT_DELEGATION_CODE, TOOLING_ENTRYPOINT_LINE_COUNT_CODE,
    TOOLING_ENTRYPOINT_SHAPE_CODE,
};
use crate::rules::models::{NativeFaultRow, NativeRuleContext};

use crate::rules::helpers::roles::{location_fault, path_fault, path_name};

const BUILD_PARSER_FUNCTION: &str = "_build_parser";
const CLASSES_ROLE: &str = "classes";
const EXCEPTIONS_ROLE: &str = "exceptions";
const INIT_FILE_NAME: &str = "__init__.py";
const MAIN_FUNCTION: &str = "main";
const MAX_FILE_LINES_THRESHOLD: &str = "max_file_lines";
const MAX_SCRIPT_ENTRYPOINT_LINES_THRESHOLD: &str = "max_script_entrypoint_lines";
const MAXIMUM_ENTRY_PRIVATE_FUNCTIONS: usize = 2;
const PARSE_ARGS_FUNCTION: &str = "_parse_args";
const PYTHON_SUFFIX: &str = ".py";
const TOOLING_SCOPE: &str = "tooling";

pub(crate) fn surface_faults(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Option<Vec<NativeFaultRow>> {
    let declarations = program.declaration_rows();
    let faults = match code {
        ENTRY_MODULE_SHAPE_CODE => entry_module_shape_faults(code, context, declarations),
        INIT_MODULE_EMPTY_CODE => init_module_faults(code, context, declarations),
        NO_REEXPORT_SHIM_CODE => reexport_faults(code, context, declarations),
        PUBLIC_SURFACE_SHAPE_CODE => public_surface_faults(code, context, declarations),
        CLASSES_ONE_CLASS_PER_MODULE_CODE => classes_shape_faults(code, context, declarations),
        SOURCE_FILE_LINE_COUNT_CODE => line_count_faults(
            program,
            code,
            context,
            MAX_FILE_LINES_THRESHOLD,
            "source file has",
            false,
        ),
        TOOLING_ENTRYPOINT_SHAPE_CODE => {
            tooling_entrypoint_shape_faults(code, context, declarations)
        }
        TOOLING_ENTRYPOINT_DELEGATION_CODE => {
            tooling_entrypoint_delegation_faults(code, context, declarations)
        }
        TOOLING_ENTRYPOINT_LINE_COUNT_CODE => line_count_faults(
            program,
            code,
            context,
            MAX_SCRIPT_ENTRYPOINT_LINES_THRESHOLD,
            "direct script has",
            true,
        ),
        _ => return None,
    };
    Some(faults)
}

fn entry_module_shape_faults(
    code: &str,
    context: &NativeRuleContext,
    declarations: &ModuleDeclarationRows,
) -> Vec<NativeFaultRow> {
    if !context.is_entry_module {
        return Vec::new();
    }
    let public_functions: Vec<&ModuleStatementRow> = declarations
        .statements
        .iter()
        .filter(|row| {
            row.function_name
                .as_ref()
                .is_some_and(|name| !name.starts_with('_'))
        })
        .collect();
    let private_functions: Vec<&ModuleStatementRow> = declarations
        .statements
        .iter()
        .filter(|row| {
            row.function_name
                .as_ref()
                .is_some_and(|name| name.starts_with('_'))
        })
        .collect();
    let mut faults = Vec::new();
    if public_functions.len() != 1 {
        faults.push(path_fault(
            code,
            Some("entry modules need one public function"),
        ));
    }
    if let Some(row) = private_functions.get(MAXIMUM_ENTRY_PRIVATE_FUNCTIONS) {
        faults.push(location_fault(
            code,
            row.line,
            row.column,
            Some("main/ entry modules may define at most two private glue functions"),
        ));
    }
    faults.extend(
        declarations
            .statements
            .iter()
            .filter(|row| !row.import_statement && row.function_name.is_none())
            .map(|row| {
                location_fault(
                    code,
                    row.line,
                    row.column,
                    Some("main/ entry modules may contain only imports and top-level functions"),
                )
            }),
    );
    faults
}

fn init_module_faults(
    code: &str,
    context: &NativeRuleContext,
    declarations: &ModuleDeclarationRows,
) -> Vec<NativeFaultRow> {
    if path_name(context) != Some(INIT_FILE_NAME)
        || context.relative_parts.len() == 1
        || declarations.empty_or_docstring_only
    {
        return Vec::new();
    }
    vec![path_fault(code, Some("nested __init__.py must be empty"))]
}

fn reexport_faults(
    code: &str,
    context: &NativeRuleContext,
    declarations: &ModuleDeclarationRows,
) -> Vec<NativeFaultRow> {
    if path_name(context) == Some(INIT_FILE_NAME)
        || context.role.as_deref() == Some(EXCEPTIONS_ROLE)
        || !declarations.pure_reexport
    {
        return Vec::new();
    }
    vec![path_fault(
        code,
        Some("internal modules must not be re-export shims"),
    )]
}

fn public_surface_faults(
    code: &str,
    context: &NativeRuleContext,
    declarations: &ModuleDeclarationRows,
) -> Vec<NativeFaultRow> {
    if path_name(context) != Some(INIT_FILE_NAME) || context.relative_parts.len() != 1 {
        return Vec::new();
    }
    let mut faults = Vec::new();
    let mut saw_all = false;
    for row in &declarations.statements {
        if row.docstring_statement || row.import_statement {
            continue;
        }
        if row.all_assignment {
            if saw_all {
                faults.push(location_fault(
                    code,
                    row.line,
                    row.column,
                    Some("public surface may define __all__ once"),
                ));
            }
            saw_all = true;
        } else {
            faults.push(location_fault(code, row.line, row.column, None));
        }
    }
    faults
}

fn classes_shape_faults(
    code: &str,
    context: &NativeRuleContext,
    declarations: &ModuleDeclarationRows,
) -> Vec<NativeFaultRow> {
    if context.role.as_deref() != Some(CLASSES_ROLE)
        || path_name(context) == Some(INIT_FILE_NAME)
        || declarations.top_level_class_count == 1
    {
        return Vec::new();
    }
    vec![path_fault(
        code,
        Some("classes modules must define one class"),
    )]
}

fn line_count_faults(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
    threshold: &str,
    message_prefix: &str,
    direct_tooling_only: bool,
) -> Vec<NativeFaultRow> {
    if direct_tooling_only && !is_direct_tooling_entrypoint(context) {
        return Vec::new();
    }
    let Some(limit) = context.thresholds.get(threshold).copied() else {
        return Vec::new();
    };
    let count = u32::try_from(program.source_line_count()).unwrap_or(u32::MAX);
    if count <= limit {
        return Vec::new();
    }
    let message = if direct_tooling_only {
        format!("{message_prefix} {count} lines (limit: {limit})")
    } else {
        format!("{message_prefix} {count} lines")
    };
    vec![path_fault(code, Some(&message))]
}

fn tooling_entrypoint_shape_faults(
    code: &str,
    context: &NativeRuleContext,
    declarations: &ModuleDeclarationRows,
) -> Vec<NativeFaultRow> {
    if !is_direct_tooling_entrypoint(context) {
        return Vec::new();
    }
    let public_functions: Vec<&ModuleStatementRow> = declarations
        .statements
        .iter()
        .filter(|row| {
            row.function_name
                .as_ref()
                .is_some_and(|name| !name.starts_with('_'))
        })
        .collect();
    let main_count = public_functions
        .iter()
        .filter(|row| row.function_name.as_deref() == Some(MAIN_FUNCTION))
        .count();
    let mut faults = Vec::new();
    if public_functions.is_empty() || main_count > 1 {
        faults.push(path_fault(
            code,
            Some("direct scripts must define exactly one public main() function"),
        ));
    }
    for row in &declarations.statements {
        if row.import_statement {
            continue;
        }
        if let Some(name) = row.function_name.as_deref() {
            if matches!(
                name,
                MAIN_FUNCTION | PARSE_ARGS_FUNCTION | BUILD_PARSER_FUNCTION
            ) {
                continue;
            }
            faults.push(location_fault(
                code,
                row.line,
                row.column,
                Some("direct scripts may define only main(), _parse_args(), and _build_parser()"),
            ));
        } else if !row.nonexecuting_import_guard {
            faults.push(location_fault(
                code,
                row.line,
                row.column,
                Some("direct scripts may contain only imports, command functions, and guards"),
            ));
        }
    }
    faults
}

fn tooling_entrypoint_delegation_faults(
    code: &str,
    context: &NativeRuleContext,
    declarations: &ModuleDeclarationRows,
) -> Vec<NativeFaultRow> {
    if !is_direct_tooling_entrypoint(context) {
        return Vec::new();
    }
    if !declarations
        .statements
        .iter()
        .any(|row| row.function_name.as_deref() == Some(MAIN_FUNCTION))
    {
        return vec![path_fault(
            code,
            Some("direct scripts must import and call an entry function from a main/ module"),
        )];
    }
    let delegates = declarations.main_calls.iter().any(|call| {
        call.name.as_ref().is_some_and(|name| {
            declarations
                .imported_main_entry_names
                .iter()
                .any(|entry| entry == name)
        })
    });
    let mut faults = Vec::new();
    if !delegates {
        faults.push(path_fault(
            code,
            Some("direct scripts must import and call an entry function from a main/ module"),
        ));
    }
    faults.extend(declarations.main_calls.iter().filter_map(|call| {
        let allowed = call.name.as_deref() == Some(PARSE_ARGS_FUNCTION)
            || call.name.as_ref().is_some_and(|name| {
                declarations
                    .imported_main_entry_names
                    .iter()
                    .any(|entry| entry == name)
            });
        (!allowed).then(|| {
            location_fault(
                code,
                call.line,
                call.column,
                Some("direct script main() may call only _parse_args() and imported main/ entries"),
            )
        })
    }));
    faults
}

fn is_direct_tooling_entrypoint(context: &NativeRuleContext) -> bool {
    context.scope == TOOLING_SCOPE
        && context.relative_parts.len() == 1
        && path_name(context)
            .is_some_and(|name| name.ends_with(PYTHON_SUFFIX) && name != INIT_FILE_NAME)
}
