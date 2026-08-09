use std::collections::HashSet;

use fensu_facts::extension::models::ProgramHandle;

use crate::rules::_helpers::dagster::assets::import_target;
use crate::rules::_helpers::dagster::source::{
    project_module_literal, quoted_strings, source_position,
};
use crate::rules::_helpers::dagster::{
    fault, file_name, module_name, path_fault, AUTOMATION_ROLES, BANNED_PACKAGES,
};
use crate::rules::models::{NativeFaultRow, NativeProjectPlane, NativeRuleContext};

const CLASSES_ROLE: &str = "_classes";
const DEFINITIONS_ROLE: &str = "defs";
const DEFINITIONS_FILE: &str = "definitions.py";
const E2E_TEST_ROOT: &str = "e2e";
const EXCEPTIONS_ROLE: &str = "exceptions";
const HELPERS_ROLE: &str = "_helpers";
const INIT_FILE: &str = "__init__.py";
const MODELS_ROLE: &str = "models";
const PRIVATE_ALIAS_PARTS: usize = 4;
const PYTHON_CACHE: &str = "__pycache__";
const ROOT_SCOPE: &str = "root";
const SOURCE_ANCHOR_PARTS: [&str; 2] = [DEFINITIONS_ROLE, INIT_FILE];
const TEST_SCOPE: &str = "test";
const TYPES_ROLE: &str = "types";
const UNIT_TEST_ROOT: &str = "unit";
const INTEGRATION_TEST_ROOT: &str = "integration";
const DBT_TEST_ROOT: &str = "dbt";
const UTILS_ROLE: &str = "utils";

pub(super) fn no_dynamic_module_references(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    if context.scope != ROOT_SCOPE {
        return Vec::new();
    }
    let mut faults: Vec<NativeFaultRow> = program
        .named_call_rows()
        .iter()
        .filter(|call| matches!(call.name.as_deref(), Some("__import__" | "import_module")))
        .map(|call| fault(code, call.line, call.column))
        .collect();
    let dynamic_lines: HashSet<u32> = faults.iter().map(|item| item.line).collect();
    for (offset, value) in quoted_strings(program.source()) {
        if project_module_literal(&value, context) {
            let (line, column) = source_position(program.source(), offset);
            if !dynamic_lines.contains(&line) {
                faults.push(fault(code, line, column));
            }
        }
    }
    faults.sort_by_key(|item| (item.line, item.column));
    faults.dedup_by_key(|item| (item.line, item.column));
    faults
}

fn private_alias(context: &NativeRuleContext, name: &str) -> bool {
    let parts = &context.relative_parts;
    parts.len() == PRIVATE_ALIAS_PARTS
        && parts.first().map(String::as_str) == Some(DEFINITIONS_ROLE)
        && parts
            .get(1)
            .is_some_and(|part| AUTOMATION_ROLES.contains(&part.as_str()))
        && file_name(context) == format!("_{name}.py")
}

pub(super) fn model_placement(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    if context.scope != ROOT_SCOPE || context.role.as_deref() == Some(MODELS_ROLE) {
        return Vec::new();
    }
    if private_alias(context, MODELS_ROLE) {
        return program
            .declaration_rows()
            .statements
            .iter()
            .filter(|row| !row.import_statement && !row.model_class)
            .map(|row| fault(code, row.line, row.column))
            .collect();
    }
    program
        .declaration_rows()
        .model_locations
        .iter()
        .map(|(line, column)| fault(code, *line, *column))
        .collect()
}

pub(super) fn exception_placement(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    if context.scope != ROOT_SCOPE || context.role.as_deref() == Some(EXCEPTIONS_ROLE) {
        return Vec::new();
    }
    if private_alias(context, EXCEPTIONS_ROLE) {
        return program
            .declaration_rows()
            .statements
            .iter()
            .filter(|row| !row.import_statement && !row.exception_class)
            .map(|row| fault(code, row.line, row.column))
            .collect();
    }
    program
        .declaration_rows()
        .exception_locations
        .iter()
        .map(|(line, column)| fault(code, *line, *column))
        .collect()
}

pub(super) fn type_placement(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    if context.scope != ROOT_SCOPE || context.role.as_deref() == Some(TYPES_ROLE) {
        return Vec::new();
    }
    if private_alias(context, TYPES_ROLE) {
        return program
            .declaration_rows()
            .statements
            .iter()
            .filter(|row| {
                !row.import_statement
                    && !row.type_class
                    && !row.explicit_type_alias
                    && !row.type_checking_import_block
            })
            .map(|row| fault(code, row.line, row.column))
            .collect();
    }
    program
        .declaration_rows()
        .type_declarations
        .iter()
        .map(|row| fault(code, row.line, row.column))
        .collect()
}

fn private_package_owner(target: &str) -> Option<String> {
    let parts: Vec<&str> = target.split('.').collect();
    parts
        .iter()
        .enumerate()
        .filter(|(_, part)| matches!(**part, HELPERS_ROLE | CLASSES_ROLE))
        .map(|(index, _)| parts[..index].join("."))
        .next()
}

pub(super) fn private_helper_boundary(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    if context.scope != ROOT_SCOPE {
        return Vec::new();
    }
    let importer = module_name(context);
    let mut faults: Vec<NativeFaultRow> = Vec::new();
    for row in &program.reference_rows().imports {
        for target in import_target(row) {
            if let Some(owner) = private_package_owner(&target) {
                if importer != owner && !importer.starts_with(&format!("{owner}.")) {
                    faults.push(fault(code, row.line, row.column));
                    break;
                }
            }
        }
    }
    if context
        .relative_parts
        .iter()
        .any(|part| part == HELPERS_ROLE)
    {
        faults.extend(
            program
                .declaration_rows()
                .statements
                .iter()
                .filter(|row| invalid_helper_statement(row))
                .map(|row| fault(code, row.line, row.column)),
        );
    }
    faults
}

pub(super) fn private_classes_shape(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    if context.scope != ROOT_SCOPE
        || !context
            .relative_parts
            .iter()
            .any(|part| part == CLASSES_ROLE)
    {
        return Vec::new();
    }
    program
        .declaration_rows()
        .statements
        .iter()
        .filter(|row| {
            if row.import_statement || row.type_checking_import_block || row.docstring_statement {
                return false;
            }
            row.class_name
                .as_ref()
                .is_none_or(|name| !name.starts_with('_'))
        })
        .map(|row| fault(code, row.line, row.column))
        .collect()
}

fn source_anchor(context: &NativeRuleContext) -> bool {
    context.scope == ROOT_SCOPE && context.relative_parts == SOURCE_ANCHOR_PARTS
}

fn scope_root_path(context: &NativeRuleContext, scope: &str) -> Option<String> {
    context
        .scope_roots
        .iter()
        .find_map(|(kind, path)| (kind == scope).then(|| path.clone()))
}

pub(super) fn source_root_allowlist(
    code: &str,
    context: &NativeRuleContext,
    project: &NativeProjectPlane,
) -> Vec<NativeFaultRow> {
    if !source_anchor(context) {
        return Vec::new();
    }
    let Some(root) = scope_root_path(context, ROOT_SCOPE) else {
        return Vec::new();
    };
    let mut invalid: HashSet<String> = HashSet::new();
    for module in &project.modules {
        if module.scope != ROOT_SCOPE || !module.path.starts_with(&format!("{root}/")) {
            continue;
        }
        let relative = module.path.trim_start_matches(&format!("{root}/"));
        let mut parts = relative.split('/');
        let first = parts.next().unwrap_or("");
        if relative.contains('/') {
            if !matches!(first, DEFINITIONS_ROLE | UTILS_ROLE | PYTHON_CACHE) {
                invalid.insert(format!("{root}/{first}"));
            }
        } else if !matches!(first, INIT_FILE | DEFINITIONS_FILE) {
            invalid.insert(module.path.clone());
        }
    }
    let mut paths: Vec<String> = invalid.into_iter().collect();
    paths.sort();
    paths
        .into_iter()
        .map(|path| path_fault(code, Some(path)))
        .collect()
}

pub(super) fn tooling_import_boundary(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    if context.scope != ROOT_SCOPE {
        return Vec::new();
    }
    program
        .reference_rows()
        .imports
        .iter()
        .filter(|row| imports_tooling_package(row, context))
        .map(|row| fault(code, row.line, row.column))
        .collect()
}

pub(super) fn runtime_package_owner(
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    if !matches!(context.scope.as_str(), ROOT_SCOPE | TEST_SCOPE) {
        return Vec::new();
    }
    let mut parts =
        context.relative_parts[..context.relative_parts.len().saturating_sub(1)].to_vec();
    if context.scope == TEST_SCOPE && !parts.is_empty() {
        if parts
            .first()
            .is_some_and(|part| context.test_scopes.contains(part))
        {
            let _ = parts.remove(0);
        }
        if !parts.is_empty() {
            let _ = parts.remove(0);
        }
    }
    parts
        .iter()
        .enumerate()
        .filter(|(index, part)| {
            BANNED_PACKAGES.contains(&part.as_str())
                && !(*index == 0 && part.as_str() == UTILS_ROLE)
        })
        .map(|_| path_fault(code, None))
        .collect()
}

pub(super) fn test_root_allowlist(
    code: &str,
    context: &NativeRuleContext,
    project: &NativeProjectPlane,
) -> Vec<NativeFaultRow> {
    if !source_anchor(context) {
        return Vec::new();
    }
    let roots: Vec<&str> = context
        .scope_roots
        .iter()
        .filter_map(|(kind, path)| (kind == TEST_SCOPE).then_some(path.as_str()))
        .collect();
    let mut invalid: HashSet<String> = HashSet::new();
    for module in project
        .modules
        .iter()
        .filter(|module| module.scope == TEST_SCOPE)
    {
        for root in &roots {
            if let Some(relative) = module.path.strip_prefix(&format!("{root}/")) {
                let first = relative.split('/').next().unwrap_or("");
                if !matches!(
                    first,
                    UNIT_TEST_ROOT
                        | INTEGRATION_TEST_ROOT
                        | E2E_TEST_ROOT
                        | DBT_TEST_ROOT
                        | PYTHON_CACHE
                ) {
                    invalid.insert(format!("{root}/{first}"));
                }
            }
        }
    }
    let mut paths: Vec<String> = invalid.into_iter().collect();
    paths.sort();
    paths
        .into_iter()
        .map(|path| path_fault(code, Some(path)))
        .collect()
}

fn invalid_helper_statement(row: &fensu_facts::facts::models::ModuleStatementRow) -> bool {
    let public_class = row
        .class_name
        .as_ref()
        .is_some_and(|name| !name.starts_with('_'));
    let public_assignment = row
        .assignment_target_names
        .iter()
        .any(|name| !name.starts_with('_'));
    public_class || public_assignment
}

fn imports_tooling_package(
    row: &fensu_facts::facts::models::ImportRow,
    context: &NativeRuleContext,
) -> bool {
    for target in import_target(row) {
        for package in &context.tooling_packages {
            if target == *package || target.starts_with(&format!("{package}.")) {
                return true;
            }
        }
    }
    false
}
