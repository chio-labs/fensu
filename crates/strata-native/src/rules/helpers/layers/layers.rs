//! Layer-family policy over shared reference rows.

use strata_facts::extension::models::ProgramHandle;
use strata_facts::facts::models::ImportRow;

use crate::rules::constants::{
    ABSOLUTE_IMPORTS_ONLY_CODE, NO_CROSS_DOMAIN_PRIVATE_MAIN_IMPORTS_CODE,
    NO_CROSS_PACKAGE_INTERNALS_CODE, NO_SIBLING_PACKAGE_INTERNALS_CODE, NO_STAR_IMPORTS_CODE,
    STAR_IMPORT_NAME,
};
use crate::rules::helpers::layer_local::local_layer_faults;
use crate::rules::helpers::roles::location_fault;
use crate::rules::models::{NativeFaultRow, NativeProjectQuery, NativeRuleContext};

const INIT_FILE_NAME: &str = "__init__.py";
const INIT_MODULE_STEM: &str = "__init__";
const HELPERS_ROLE_NAME: &str = "_helpers";
const ROOT_SCOPE: &str = "root";

pub(crate) fn layer_faults(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Option<Vec<NativeFaultRow>> {
    let rows = program.reference_rows();
    let faults = match code {
        ABSOLUTE_IMPORTS_ONLY_CODE => rows
            .imports
            .iter()
            .filter(|row| row.from_import && row.relative_level > 0)
            .map(|row| location_fault(code, row.line, row.column, None))
            .collect(),
        NO_STAR_IMPORTS_CODE => rows
            .imports
            .iter()
            .filter(|row| {
                row.from_import
                    && row
                        .aliases
                        .iter()
                        .any(|alias| alias.imported_name == STAR_IMPORT_NAME)
            })
            .map(|row| location_fault(code, row.line, row.column, None))
            .collect(),
        NO_SIBLING_PACKAGE_INTERNALS_CODE | NO_CROSS_PACKAGE_INTERNALS_CODE => {
            ownership_faults(code, context, &rows.imports)
        }
        NO_CROSS_DOMAIN_PRIVATE_MAIN_IMPORTS_CODE => {
            private_main_import_faults(code, context, &rows.imports)
        }
        _ => return local_layer_faults(program, code, context),
    };
    Some(faults)
}

#[derive(Clone)]
struct Ownership {
    package: Option<String>,
    owner_prefix: Vec<String>,
    domain: Option<String>,
    first_role: Option<String>,
    tail: Vec<String>,
}

fn ownership_faults(
    code: &str,
    context: &NativeRuleContext,
    imports: &[ImportRow],
) -> Vec<NativeFaultRow> {
    let current_parts = current_module_parts(context);
    let current = classify(&current_parts, file_name(context) == INIT_FILE_NAME);
    let mut faults = Vec::new();
    for row in imports {
        for target_parts in
            normalized_targets(row, &current_parts, file_name(context) == INIT_FILE_NAME)
        {
            let initializer = module_init_path(context, &target_parts)
                .is_some_and(|path| observed_bool(context, "exists", &path));
            let target = classify(&target_parts, initializer);
            let violation = if code == NO_SIBLING_PACKAGE_INTERNALS_CODE {
                sibling_internal(&current, &target)
            } else {
                cross_package_internal(&current, &target)
            };
            if violation {
                let imported = target_parts.join(".");
                let message = if code == NO_SIBLING_PACKAGE_INTERNALS_CODE {
                    format!("import '{imported}' reaches into sibling internals")
                } else {
                    let package = target_parts
                        .iter()
                        .take(2)
                        .cloned()
                        .collect::<Vec<_>>()
                        .join(".");
                    format!("import '{imported}' reaches into internal structure of '{package}'")
                };
                faults.push(message_fault(code, row.line, row.column, message));
                break;
            }
        }
    }
    faults
}

fn private_main_import_faults(
    code: &str,
    context: &NativeRuleContext,
    imports: &[ImportRow],
) -> Vec<NativeFaultRow> {
    let current_parts = current_module_parts(context);
    let current = classify(&current_parts, file_name(context) == INIT_FILE_NAME);
    let mut faults = Vec::new();
    for row in imports {
        let bases = normalized_targets(row, &current_parts, file_name(context) == INIT_FILE_NAME);
        let mut targets = bases.clone();
        if row.from_import {
            for base in bases {
                for alias in &row.aliases {
                    let mut target = base.clone();
                    target.extend(alias.imported_name.split('.').map(str::to_owned));
                    if !targets.contains(&target) {
                        targets.push(target);
                    }
                }
            }
        }
        for parts in targets {
            let target = classify(&parts, false);
            if !private_main(&target) || shares_domain(&current, &target) {
                continue;
            }
            let exists = module_file_path(context, &parts)
                .is_some_and(|path| observed_bool(context, "is_file", &path));
            if exists {
                faults.push(message_fault(
                    code,
                    row.line,
                    row.column,
                    format!(
                        "import '{}' reaches a domain-private main entry",
                        parts.join(".")
                    ),
                ));
                break;
            }
        }
    }
    faults
}

fn classify(parts: &[String], initializer: bool) -> Ownership {
    let structural = [
        "main",
        "_helpers",
        "classes",
        "models",
        "types",
        "constants",
        "exceptions",
    ];
    let role_index = parts
        .iter()
        .enumerate()
        .skip(1)
        .find_map(|(index, part)| structural.contains(&part.as_str()).then_some(index));
    let (owner_prefix, first_role, tail) = if let Some(index) = role_index {
        let role = if parts[index] == HELPERS_ROLE_NAME {
            "helpers".to_owned()
        } else {
            parts[index].clone()
        };
        (
            parts[1..index].to_vec(),
            Some(role),
            parts[index + 1..].to_vec(),
        )
    } else {
        let end = if initializer {
            parts.len()
        } else {
            parts.len().saturating_sub(1).max(1)
        };
        (parts[1..end].to_vec(), None, parts[end..].to_vec())
    };
    Ownership {
        package: parts.first().cloned(),
        domain: owner_prefix.first().cloned(),
        owner_prefix,
        first_role,
        tail,
    }
}

fn public_surface(target: &Ownership) -> bool {
    target.first_role.as_deref().is_some_and(|role| {
        matches!(
            role,
            "main" | "classes" | "models" | "types" | "constants" | "exceptions"
        )
    })
}

fn sibling_internal(current: &Ownership, target: &Ownership) -> bool {
    current.package.is_some()
        && current.package == target.package
        && current.domain.is_some()
        && current.domain == target.domain
        && current.owner_prefix != target.owner_prefix
        && !public_surface(target)
}

fn cross_package_internal(current: &Ownership, target: &Ownership) -> bool {
    current.package.is_some()
        && current.package == target.package
        && current.domain.is_some()
        && target.domain.is_some()
        && current.domain != target.domain
        && !public_surface(target)
}

fn private_main(target: &Ownership) -> bool {
    target.first_role.as_deref() == Some("main")
        && target
            .tail
            .last()
            .is_some_and(|name| name.starts_with('_') && !name.starts_with("__"))
}

fn shares_domain(current: &Ownership, target: &Ownership) -> bool {
    current.package.is_some()
        && current.package == target.package
        && current.domain.is_some()
        && current.domain == target.domain
}

fn normalized_targets(
    row: &ImportRow,
    current_parts: &[String],
    current_initializer: bool,
) -> Vec<Vec<String>> {
    if !row.from_import {
        return row
            .aliases
            .iter()
            .map(|alias| alias.imported_name.split('.').map(str::to_owned).collect())
            .collect();
    }
    if row.relative_level == 0 {
        return (!row.module_parts.is_empty())
            .then(|| row.module_parts.clone())
            .into_iter()
            .collect();
    }
    if row.module_parts.is_empty() {
        return Vec::new();
    }
    let mut base = if current_initializer {
        current_parts.to_vec()
    } else {
        current_parts[..current_parts.len().saturating_sub(1)].to_vec()
    };
    let parents = row.relative_level.saturating_sub(1) as usize;
    if parents > base.len() {
        return Vec::new();
    }
    base.truncate(base.len() - parents);
    base.extend(row.module_parts.clone());
    vec![base]
}

fn current_module_parts(context: &NativeRuleContext) -> Vec<String> {
    let mut parts = vec![context.package_name.clone()];
    parts.extend(context.relative_parts.iter().cloned());
    if let Some(last) = parts.last_mut() {
        *last = last.strip_suffix(".py").unwrap_or(last).to_owned();
    }
    if parts.last().is_some_and(|part| part == INIT_MODULE_STEM) {
        let _ = parts.pop();
    }
    parts
}

fn file_name(context: &NativeRuleContext) -> &str {
    context.relative_parts.last().map_or("", String::as_str)
}

fn runtime_root<'a>(context: &'a NativeRuleContext, package: &str) -> Option<&'a str> {
    context.scope_roots.iter().find_map(|(scope, root)| {
        (scope == ROOT_SCOPE && root.rsplit('/').next() == Some(package)).then_some(root.as_str())
    })
}

fn module_init_path(context: &NativeRuleContext, parts: &[String]) -> Option<String> {
    let root = runtime_root(context, parts.first()?)?;
    let parent = root.rsplit_once('/').map_or("", |item| item.0);
    Some(format!("{parent}/{}/{INIT_FILE_NAME}", parts.join("/")))
}

fn module_file_path(context: &NativeRuleContext, parts: &[String]) -> Option<String> {
    let root = runtime_root(context, parts.first()?)?;
    let parent = root.rsplit_once('/').map_or("", |item| item.0);
    Some(format!("{parent}/{}.py", parts.join("/")))
}

fn observed_bool(context: &NativeRuleContext, kind: &str, path: &str) -> bool {
    context.observation(&NativeProjectQuery {
        kind: kind.to_owned(),
        path: path.to_owned(),
        argument: String::new(),
    }) == ["true"]
}

fn message_fault(code: &str, line: u32, column: u32, message: String) -> NativeFaultRow {
    NativeFaultRow {
        code: code.to_owned(),
        line,
        column,
        message: Some(message),
        remediation: None,
        path: None,
    }
}
