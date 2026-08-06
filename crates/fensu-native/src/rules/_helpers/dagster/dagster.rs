//! Native policy for the shipped Dagster rule pack.

use fensu_facts::extension::models::ProgramHandle;

use crate::rules::constants::{
    DAGSTER_ASSETS_DELEGATE_TO_MAIN_CODE, DAGSTER_ASSETS_MODULE_SHAPE_CODE,
    DAGSTER_ASSET_CALLBACK_SIGNATURE_CODE, DAGSTER_ASSET_CONFIG_SHAPE_CODE,
    DAGSTER_ASSET_PACKAGE_LAYOUT_CODE, DAGSTER_AUTOLOAD_EXTERNAL_DISCOVERY_CODE,
    DAGSTER_DEFINITION_MODULE_LAYOUT_CODE, DAGSTER_DEFINITION_PUBLIC_SURFACE_CODE,
    DAGSTER_EXCEPTION_PLACEMENT_CODE, DAGSTER_IMPORT_BOUNDARIES_CODE,
    DAGSTER_MAIN_MODULE_SHAPE_CODE, DAGSTER_MODEL_PLACEMENT_CODE,
    DAGSTER_NO_DYNAMIC_MODULE_REFERENCES_CODE, DAGSTER_OPERATIONAL_RESOURCE_LAYOUT_CODE,
    DAGSTER_PRIVATE_CLASSES_SHAPE_CODE, DAGSTER_PRIVATE_HELPER_BOUNDARY_CODE,
    DAGSTER_PRIVATE_SUPPORT_IMPORTS_CODE, DAGSTER_PROVIDER_TYPE_HONESTY_CODE,
    DAGSTER_RUNTIME_PACKAGE_OWNER_CODE, DAGSTER_SOURCE_ROOT_ALLOWLIST_CODE,
    DAGSTER_TEST_ROOT_ALLOWLIST_CODE, DAGSTER_TOOLING_IMPORT_BOUNDARY_CODE,
    DAGSTER_TYPE_PLACEMENT_CODE,
};
use crate::rules::models::{NativeFaultRow, NativeProjectPlane, NativeRuleContext};

mod assets;
mod autoload;
mod boundaries;
mod definitions;
mod source;

use assets::{
    asset_callback_signature, asset_package_layout, assets_delegate_to_main, assets_module_shape,
    import_boundaries, main_module_shape,
};
use autoload::autoload_external_discovery;
use boundaries::{
    exception_placement, model_placement, no_dynamic_module_references, private_classes_shape,
    private_helper_boundary, runtime_package_owner, source_root_allowlist, test_root_allowlist,
    tooling_import_boundary, type_placement,
};
use definitions::{
    asset_config_shape, definition_module_layout, definition_public_surface,
    operational_resource_layout, private_support_imports, provider_type_honesty,
};

pub(super) const ASSET_DECORATORS: &[&str] = &["asset", "dbt_assets", "multi_asset"];
pub(super) const AUTOMATION_ROLES: &[&str] = &["jobs", "schedules", "sensors"];
pub(super) const BANNED_PACKAGES: &[&str] = &[
    "base", "common", "helpers", "lib", "misc", "shared", "util", "utils",
];
pub(super) const PRIVATE_ROLE_FILES: &[&str] =
    &["_constants.py", "_exceptions.py", "_models.py", "_types.py"];
pub(super) const DEFINITION_FORBIDDEN_NAMES: &[&str] = &[
    "common",
    "config",
    "definitions",
    "helpers",
    "job",
    "main",
    "processing",
    "schedule",
    "sensor",
    "shared",
    "utils",
    "_job",
    "_jobs",
];
const ASSETS_BINDING: &str = "assets";
const DEFINITIONS_ROLE: &str = "defs";
const INIT_MODULE: &str = "__init__";
const POSITIONAL_ONLY_MARKER: &str = "/";

pub(crate) fn dagster_faults(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
    project: &NativeProjectPlane,
) -> Option<Result<Vec<NativeFaultRow>, String>> {
    let faults = match code {
        DAGSTER_ASSET_PACKAGE_LAYOUT_CODE => asset_package_layout(program, code, context, project),
        DAGSTER_ASSETS_MODULE_SHAPE_CODE => assets_module_shape(program, code, context),
        DAGSTER_ASSETS_DELEGATE_TO_MAIN_CODE => assets_delegate_to_main(program, code, context),
        DAGSTER_MAIN_MODULE_SHAPE_CODE => main_module_shape(program, code, context, project),
        DAGSTER_ASSET_CALLBACK_SIGNATURE_CODE => asset_callback_signature(program, code, context),
        DAGSTER_IMPORT_BOUNDARIES_CODE => import_boundaries(program, code, context, project),
        DAGSTER_DEFINITION_PUBLIC_SURFACE_CODE => definition_public_surface(program, code, context),
        DAGSTER_DEFINITION_MODULE_LAYOUT_CODE => definition_module_layout(program, code, context),
        DAGSTER_PRIVATE_SUPPORT_IMPORTS_CODE => private_support_imports(program, code, context),
        DAGSTER_OPERATIONAL_RESOURCE_LAYOUT_CODE => {
            operational_resource_layout(program, code, context)
        }
        DAGSTER_PROVIDER_TYPE_HONESTY_CODE => provider_type_honesty(program, code, context),
        DAGSTER_ASSET_CONFIG_SHAPE_CODE => asset_config_shape(program, code, context),
        DAGSTER_NO_DYNAMIC_MODULE_REFERENCES_CODE => {
            no_dynamic_module_references(program, code, context)
        }
        DAGSTER_MODEL_PLACEMENT_CODE => model_placement(program, code, context),
        DAGSTER_EXCEPTION_PLACEMENT_CODE => exception_placement(program, code, context),
        DAGSTER_PRIVATE_HELPER_BOUNDARY_CODE => private_helper_boundary(program, code, context),
        DAGSTER_PRIVATE_CLASSES_SHAPE_CODE => private_classes_shape(program, code, context),
        DAGSTER_SOURCE_ROOT_ALLOWLIST_CODE => source_root_allowlist(code, context, project),
        DAGSTER_TOOLING_IMPORT_BOUNDARY_CODE => tooling_import_boundary(program, code, context),
        DAGSTER_RUNTIME_PACKAGE_OWNER_CODE => runtime_package_owner(code, context),
        DAGSTER_TEST_ROOT_ALLOWLIST_CODE => test_root_allowlist(code, context, project),
        DAGSTER_AUTOLOAD_EXTERNAL_DISCOVERY_CODE => {
            return Some(autoload_external_discovery(program, code, context, project));
        }
        DAGSTER_TYPE_PLACEMENT_CODE => type_placement(program, code, context),
        _ => return None,
    };
    Some(Ok(faults))
}

pub(super) fn fault(code: &str, line: u32, column: u32) -> NativeFaultRow {
    NativeFaultRow {
        code: code.to_owned(),
        line,
        column,
        message: None,
        remediation: None,
        path: None,
    }
}

pub(super) fn path_fault(code: &str, path: Option<String>) -> NativeFaultRow {
    NativeFaultRow {
        path,
        ..fault(code, 1, 0)
    }
}

pub(super) fn file_name(context: &NativeRuleContext) -> &str {
    context.relative_parts.last().map_or("", String::as_str)
}

pub(super) fn module_name(context: &NativeRuleContext) -> String {
    let mut parts = vec![context.package_name.clone()];
    parts.extend(context.relative_parts.iter().cloned());
    if let Some(last) = parts.last_mut() {
        *last = last.strip_suffix(".py").unwrap_or(last).to_owned();
    }
    if parts.last().is_some_and(|part| part == INIT_MODULE) {
        let _ = parts.pop();
    }
    parts.join(".")
}

pub(super) fn in_definition_role(context: &NativeRuleContext, role: &str) -> bool {
    context
        .relative_parts
        .first()
        .is_some_and(|part| part == DEFINITIONS_ROLE)
        && context
            .relative_parts
            .get(1)
            .is_some_and(|part| part == role)
}

pub(super) fn top_level_functions(
    program: &ProgramHandle,
) -> Vec<&fensu_facts::facts::models::FunctionMetricRow> {
    let (rows, slots) = program.function_rows();
    slots.iter().filter_map(|slot| rows.get(*slot)).collect()
}

pub(super) fn decorators(program: &ProgramHandle, line: u32) -> Vec<String> {
    let lines: Vec<&str> = program.source().lines().collect();
    let mut index = usize::try_from(line.saturating_sub(1)).unwrap_or_default();
    let mut names: Vec<String> = Vec::new();
    while index > 0 {
        index -= 1;
        let text = lines.get(index).copied().unwrap_or("").trim();
        if text.is_empty() {
            continue;
        }
        if !text.starts_with('@') {
            break;
        }
        let target = text[1..].split('(').next().unwrap_or("");
        names.push(target.rsplit('.').next().unwrap_or(target).to_owned());
    }
    names
}

pub(super) fn has_decorator(program: &ProgramHandle, line: u32, names: &[&str]) -> bool {
    decorators(program, line)
        .iter()
        .any(|name| names.contains(&name.as_str()))
}

pub(super) fn function_source(program: &ProgramHandle, line: u32) -> String {
    let lines: Vec<&str> = program.source().lines().collect();
    let start = usize::try_from(line.saturating_sub(1)).unwrap_or_default();
    let indentation = lines
        .get(start)
        .map_or(0, |line| line.len().saturating_sub(line.trim_start().len()));
    let mut selected: Vec<&str> = Vec::new();
    for (index, text) in lines.iter().enumerate().skip(start) {
        if index > start
            && !text.trim().is_empty()
            && text.len().saturating_sub(text.trim_start().len()) <= indentation
        {
            break;
        }
        selected.push(text);
    }
    selected.join("\n")
}

pub(super) fn signature_source(program: &ProgramHandle, line: u32) -> String {
    let lines: Vec<&str> = program.source().lines().collect();
    let start = usize::try_from(line.saturating_sub(1)).unwrap_or_default();
    let mut signature = String::new();
    let mut balance: i32 = 0;
    for text in lines.iter().skip(start) {
        signature.push_str(text.trim());
        for character in text.chars() {
            balance += match character {
                '(' | '[' => 1,
                ')' | ']' => -1,
                _ => 0,
            };
        }
        if balance <= 0 && text.contains(':') {
            break;
        }
    }
    signature
}

pub(super) fn positional_parameter_names(program: &ProgramHandle, line: u32) -> Vec<String> {
    let signature = signature_source(program, line);
    let Some((_, after_open)) = signature.split_once('(') else {
        return Vec::new();
    };
    let before_keyword_only = after_open.split('*').next().unwrap_or(after_open);
    before_keyword_only
        .split(',')
        .map(str::trim)
        .filter(|item| !item.is_empty() && *item != POSITIONAL_ONLY_MARKER)
        .map(|item| {
            item.split([':', '='])
                .next()
                .unwrap_or(item)
                .trim()
                .to_owned()
        })
        .filter(|item| !matches!(item.as_str(), "self" | "cls"))
        .collect()
}

pub(super) fn asset_callbacks(
    program: &ProgramHandle,
) -> Vec<&fensu_facts::facts::models::FunctionMetricRow> {
    program
        .function_rows()
        .0
        .iter()
        .filter(|row| has_decorator(program, row.line, ASSET_DECORATORS))
        .collect()
}

pub(super) fn factory_backed_assets(program: &ProgramHandle) -> bool {
    program
        .declaration_rows()
        .statements
        .iter()
        .any(|row| assets_factory_statement(program, row))
}

fn assets_factory_statement(
    program: &ProgramHandle,
    row: &fensu_facts::facts::models::ModuleStatementRow,
) -> bool {
    let binds_assets = row
        .assignment_target_names
        .iter()
        .any(|name| name == ASSETS_BINDING);
    let constructs_assets = program
        .source()
        .lines()
        .nth(usize::try_from(row.line.saturating_sub(1)).unwrap_or_default())
        .is_some_and(|line| line.contains("AssetsDefinition") && line.contains('('));
    binds_assets && constructs_assets
}
