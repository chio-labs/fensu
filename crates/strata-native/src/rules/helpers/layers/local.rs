//! File-local layer policy that does not require project observations.

use std::collections::HashSet;

use strata_facts::extension::models::ProgramHandle;
use strata_facts::facts::models::{ImportRow, ReferenceEventRow};

use crate::rules::constants::{
    NO_CROSS_FILE_HELPER_PRIVATE_CLASS_CODE, NO_INTERNAL_PUBLIC_SURFACE_IMPORTS_CODE,
    NO_RUNTIME_IMPORTS_FROM_TOOLING_CODE,
};
use crate::rules::models::{NativeFaultRow, NativeRuleContext};

const HELPERS_PART: &str = "_helpers";
const INIT_FILE_NAME: &str = "__init__.py";
const ROOT_SCOPE: &str = "root";
const RULES_DOMAIN: &str = "rules";
const EXEMPLARS_SUBDOMAIN: &str = "exemplars";

pub(crate) fn local_layer_faults(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Option<Vec<NativeFaultRow>> {
    let rows = program.reference_rows();
    let faults = match code {
        NO_INTERNAL_PUBLIC_SURFACE_IMPORTS_CODE => {
            internal_public_surface_faults(code, context, &rows.imports)
        }
        NO_CROSS_FILE_HELPER_PRIVATE_CLASS_CODE => private_helper_reference_faults(program, code),
        NO_RUNTIME_IMPORTS_FROM_TOOLING_CODE => {
            runtime_tooling_import_faults(code, context, &rows.imports)
        }
        _ => return None,
    };
    Some(faults)
}

fn internal_public_surface_faults(
    code: &str,
    context: &NativeRuleContext,
    imports: &[ImportRow],
) -> Vec<NativeFaultRow> {
    if context.scope != ROOT_SCOPE
        || matches!(context.relative_parts.as_slice(), [domain, subdomain, ..] if domain == RULES_DOMAIN && subdomain == EXEMPLARS_SUBDOMAIN)
        || matches!(context.relative_parts.as_slice(), [name] if name == INIT_FILE_NAME)
    {
        return Vec::new();
    }
    imports
        .iter()
        .filter(|row| {
            if row.from_import {
                row.relative_level == 0
                    && row.module_parts.as_slice() == [context.package_name.as_str()]
            } else {
                row.aliases
                    .iter()
                    .any(|alias| alias.imported_name == context.package_name)
            }
        })
        .map(|row| location_fault(code, row.line, row.column))
        .collect()
}

fn runtime_tooling_import_faults(
    code: &str,
    context: &NativeRuleContext,
    imports: &[ImportRow],
) -> Vec<NativeFaultRow> {
    if context.scope != ROOT_SCOPE {
        return Vec::new();
    }
    imports
        .iter()
        .filter(|row| {
            if row.from_import {
                row.relative_level == 0
                    && targets_tooling(&row.module_parts, &context.tooling_packages)
            } else {
                row.aliases.iter().any(|alias| {
                    alias.imported_name.split('.').next().is_some_and(|part| {
                        context.tooling_packages.iter().any(|item| item == part)
                    })
                })
            }
        })
        .map(|row| location_fault(code, row.line, row.column))
        .collect()
}

fn targets_tooling(imported_parts: &[String], tooling_packages: &[String]) -> bool {
    imported_parts
        .first()
        .is_some_and(|part| tooling_packages.contains(part))
}

fn private_helper_reference_faults(program: &ProgramHandle, code: &str) -> Vec<NativeFaultRow> {
    let rows = program.reference_rows();
    let mut faults = Vec::new();
    let mut helper_module_aliases: HashSet<String> = HashSet::new();
    for event in &rows.events {
        match event {
            ReferenceEventRow::Import(slot) => {
                if let Some(row) = rows.imports.get(*slot) {
                    collect_import_faults(row, code, &mut helper_module_aliases, &mut faults);
                }
            }
            ReferenceEventRow::Attribute {
                line,
                column,
                base_name,
                attribute_name,
            } if is_private_class_name(attribute_name)
                && base_name
                    .as_ref()
                    .is_some_and(|name| helper_module_aliases.contains(name)) =>
            {
                faults.push(location_fault(code, *line, *column));
            }
            ReferenceEventRow::Attribute { .. } => {}
        }
    }
    faults
}

fn collect_import_faults(
    row: &ImportRow,
    code: &str,
    helper_module_aliases: &mut HashSet<String>,
    faults: &mut Vec<NativeFaultRow>,
) {
    if row.from_import {
        if !row.module_parts.iter().any(|part| part == HELPERS_PART) {
            return;
        }
        for alias in &row.aliases {
            if is_private_class_name(&alias.imported_name) {
                faults.push(location_fault(code, row.line, row.column));
            } else {
                helper_module_aliases.insert(alias.bound_name.clone());
            }
        }
        return;
    }
    for alias in &row.aliases {
        let parts: Vec<&str> = alias.imported_name.split('.').collect();
        if !parts.contains(&HELPERS_PART) {
            continue;
        }
        if parts.last().is_some_and(|name| is_private_class_name(name)) {
            faults.push(location_fault(code, row.line, row.column));
        } else {
            helper_module_aliases.insert(alias.bound_name.clone());
        }
    }
}

fn is_private_class_name(name: &str) -> bool {
    let mut characters = name.chars();
    matches!((characters.next(), characters.next()), (Some('_'), Some(second)) if second.is_uppercase())
}

fn location_fault(code: &str, line: u32, column: u32) -> NativeFaultRow {
    NativeFaultRow {
        code: code.to_owned(),
        line,
        column,
        message: None,
        remediation: None,
        path: None,
    }
}
