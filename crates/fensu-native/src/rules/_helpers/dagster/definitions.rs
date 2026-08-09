use fensu_facts::extension::models::ProgramHandle;

use crate::rules::_helpers::dagster::assets::{private_definition_support, role_parts};
use crate::rules::_helpers::dagster::{
    decorators, fault, file_name, function_source, has_decorator, in_definition_role, module_name,
    path_fault, top_level_functions, AUTOMATION_ROLES, DEFINITION_FORBIDDEN_NAMES,
    PRIVATE_ROLE_FILES,
};
use crate::rules::models::{NativeFaultRow, NativeRuleContext};

const ASSET_CONFIGS_ROLE: &str = "asset_configs";
const BASE_CONFIG_FRAGMENT: &str = "BaseConfig";
const CLASSES_ROLE: &str = "_classes";
const CONSTANTS_MODULE: &str = "_constants";
const DEFINITIONS_ROLE: &str = "defs";
const HELPERS_ROLE: &str = "_helpers";
const INIT_FILE: &str = "__init__.py";
const MINIMUM_PRIVATE_SUPPORT_PARTS: usize = 4;
const PIPELINE_MODULE: &str = "pipeline";
const PIPELINE_CONFIG_SUFFIX: &str = "PipelineConfig";
const CONFIGURABLE_RESOURCE_BASE: &str = "ConfigurableResource";
const RESOURCE_MODULE: &str = "resource";
const RESOURCES_ROLE: &str = "resources";
const ROLE_MODULE_PARTS: usize = 2;
const SENSOR_DECORATOR_SUFFIX: &str = "sensor";
const SUPPORT_MODULE_PARTS: usize = 3;

pub(super) fn definition_public_surface(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    let Some((role, _)) = role_parts(context) else {
        return Vec::new();
    };
    if private_definition_support(context) {
        return Vec::new();
    }
    let (allowed_decorators, allowed_annotations): (&[&str], &[&str]) = match role {
        "jobs" => (
            &["job", "definitions"],
            &["JobDefinition", "UnresolvedAssetJobDefinition"],
        ),
        "schedules" => (&["schedule", "definitions"], &["ScheduleDefinition"]),
        _ => (&["sensor", "definitions"], &["SensorDefinition"]),
    };
    program
        .declaration_rows()
        .statements
        .iter()
        .filter(|row| {
            invalid_public_surface_statement(program, row, allowed_decorators, allowed_annotations)
        })
        .map(|row| fault(code, row.line, row.column))
        .collect()
}

pub(super) fn definition_module_layout(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    let Some((_, parts)) = role_parts(context) else {
        return Vec::new();
    };
    let name = file_name(context).trim_end_matches(".py");
    if file_name(context) == INIT_FILE {
        let valid = parts.len() <= ROLE_MODULE_PARTS
            || (parts.len() == SUPPORT_MODULE_PARTS
                && parts.get(1).is_some_and(|part| part == HELPERS_ROLE));
        return (!valid)
            .then(|| path_fault(code, None))
            .into_iter()
            .collect();
    }
    if parts.len() == SUPPORT_MODULE_PARTS && parts.get(1).is_some_and(|part| part == HELPERS_ROLE)
    {
        return (name.starts_with('_') || DEFINITION_FORBIDDEN_NAMES.contains(&name))
            .then(|| path_fault(code, None))
            .into_iter()
            .collect();
    }
    if parts.len() != ROLE_MODULE_PARTS || DEFINITION_FORBIDDEN_NAMES.contains(&name) {
        return vec![path_fault(code, None)];
    }
    if name.starts_with('_') && !PRIVATE_ROLE_FILES.contains(&file_name(context)) {
        return vec![path_fault(code, None)];
    }
    if name == CONSTANTS_MODULE {
        return program
            .declaration_rows()
            .statements
            .iter()
            .filter(|row| invalid_constant_statement(row))
            .map(|row| fault(code, row.line, row.column))
            .collect();
    }
    Vec::new()
}

fn private_support_owner(target: &str) -> Option<String> {
    let parts: Vec<&str> = target.split('.').collect();
    if parts.len() < MINIMUM_PRIVATE_SUPPORT_PARTS
        || parts.get(1) != Some(&DEFINITIONS_ROLE)
        || !parts
            .get(2)
            .is_some_and(|part| AUTOMATION_ROLES.contains(part))
    {
        return None;
    }
    if let Some(index) = parts.iter().position(|part| *part == HELPERS_ROLE) {
        return Some(parts[..index].join("."));
    }
    if parts
        .last()
        .is_some_and(|part| matches!(*part, "_constants" | "_exceptions" | "_models" | "_types"))
    {
        return Some(parts[..parts.len() - 1].join("."));
    }
    None
}

pub(super) fn private_support_imports(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    let importer_module = module_name(context);
    let importer_parent = importer_module.rsplit_once('.').map_or("", |item| item.0);
    program
        .reference_rows()
        .imports
        .iter()
        .filter(|row| row.from_import)
        .filter_map(|row| {
            let target = row.module_parts.join(".");
            let owner = private_support_owner(&target)?;
            (importer_parent != owner && !importer_parent.starts_with(&format!("{owner}._helpers")))
                .then(|| fault(code, row.line, row.column))
        })
        .collect()
}

pub(super) fn operational_resource_layout(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    if !in_definition_role(context, "resources") {
        return Vec::new();
    }
    let parts = &context.relative_parts[2..];
    if parts.first().is_some_and(|part| part == ASSET_CONFIGS_ROLE) {
        return Vec::new();
    }
    if file_name(context) == INIT_FILE {
        if parts.len() == 1 {
            return Vec::new();
        }
        let valid = parts.len() == ROLE_MODULE_PARTS
            || (parts.len() == SUPPORT_MODULE_PARTS
                && matches!(
                    parts.get(1).map(String::as_str),
                    Some(CLASSES_ROLE | HELPERS_ROLE)
                ));
        return (!valid)
            .then(|| path_fault(code, None))
            .into_iter()
            .collect();
    }
    let name = file_name(context).trim_end_matches(".py");
    if parts.len() == ROLE_MODULE_PARTS
        && ["constants", "exceptions", "models", "resource", "types"].contains(&name)
    {
        if name == RESOURCE_MODULE {
            let providers: Vec<_> = top_level_functions(program)
                .into_iter()
                .filter(|row| has_decorator(program, row.line, &["definitions"]))
                .collect();
            if providers.len() != 1
                || !function_source(program, providers[0].line).contains("resources=")
            {
                return vec![path_fault(code, None)];
            }
        }
        return Vec::new();
    }
    let helper_valid = parts.len() == SUPPORT_MODULE_PARTS
        && parts.get(1).is_some_and(|part| part == HELPERS_ROLE)
        && ![
            "constants",
            "definitions",
            "exceptions",
            "models",
            "processing",
            "resource",
            "types",
        ]
        .contains(&name);
    let class_valid = parts.len() == SUPPORT_MODULE_PARTS
        && parts.get(1).is_some_and(|part| part == CLASSES_ROLE)
        && ![
            "classes",
            "constants",
            "definitions",
            "exceptions",
            "models",
            "resource",
            "types",
        ]
        .contains(&name);
    (!helper_valid && !class_valid)
        .then(|| path_fault(code, None))
        .into_iter()
        .collect()
}

pub(super) fn provider_type_honesty(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    if role_parts(context).is_none() {
        return Vec::new();
    }
    program
        .named_call_rows()
        .iter()
        .filter(|call| call.name.as_deref() == Some("cast"))
        .filter(|call| {
            let line = program
                .source()
                .lines()
                .nth(usize::try_from(call.line.saturating_sub(1)).unwrap_or_default())
                .unwrap_or("");
            line.contains("definitions(") || line.contains("Definitions(")
        })
        .map(|call| fault(code, call.line, call.column))
        .collect()
}

pub(super) fn asset_config_shape(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    let parts = &context.relative_parts;
    if parts.first().map(String::as_str) != Some(DEFINITIONS_ROLE)
        || parts.get(1).map(String::as_str) != Some(RESOURCES_ROLE)
        || parts.get(2).map(String::as_str) != Some(ASSET_CONFIGS_ROLE)
        || file_name(context) == INIT_FILE
    {
        return Vec::new();
    }
    let module = file_name(context).trim_end_matches(".py");
    if parts.iter().any(|part| part == HELPERS_ROLE) {
        let valid = parts
            .get(parts.len().saturating_sub(2))
            .is_some_and(|part| part == HELPERS_ROLE)
            && !module.starts_with('_')
            && !["common", "helpers", "shared", "utils"].contains(&module);
        return (!valid)
            .then(|| path_fault(code, None))
            .into_iter()
            .collect();
    }
    if matches!(module, "exceptions" | "models") {
        return Vec::new();
    }
    if [
        "base_config",
        "common",
        "config",
        "definitions",
        "helpers",
        "shared",
        "utils",
    ]
    .contains(&module)
    {
        return vec![path_fault(code, None)];
    }
    let public_classes: Vec<_> = program
        .class_declaration_rows()
        .iter()
        .filter(|row| row.top_level && !row.name.starts_with('_'))
        .collect();
    let configs: Vec<_> = public_classes
        .iter()
        .filter(|row| row.name.ends_with("Config"))
        .copied()
        .collect();
    let providers: Vec<_> = top_level_functions(program)
        .into_iter()
        .filter(|row| has_decorator(program, row.line, &["definitions"]))
        .collect();
    let mut faults: Vec<NativeFaultRow> = Vec::new();
    if public_classes.len() != 1 || configs.len() != 1 || providers.len() != 1 {
        faults.push(path_fault(code, None));
    }
    for class in configs {
        if class.name.contains(BASE_CONFIG_FRAGMENT)
            || (module == PIPELINE_MODULE
                && (!class.name.ends_with(PIPELINE_CONFIG_SUFFIX)
                    || !class
                        .base_names
                        .iter()
                        .any(|base| base == CONFIGURABLE_RESOURCE_BASE)))
        {
            faults.push(fault(code, class.line, class.column));
        }
        if providers.len() == 1
            && !function_source(program, providers[0].line).contains(&format!("{}(", class.name))
        {
            faults.push(fault(code, providers[0].line, providers[0].column));
        }
    }
    faults
}

fn invalid_public_surface_statement(
    program: &ProgramHandle,
    row: &fensu_facts::facts::models::ModuleStatementRow,
    allowed_decorators: &[&str],
    allowed_annotations: &[&str],
) -> bool {
    if row.import_statement || row.docstring_statement {
        return false;
    }
    if !row.assignment_target_names.is_empty()
        && row
            .assignment_target_names
            .iter()
            .all(|name| name.starts_with('_'))
    {
        return false;
    }
    if row.assignment_statement {
        return !assignment_annotation(program, row.line)
            .is_some_and(|annotation| allowed_annotations.contains(&annotation.as_str()));
    }
    if let Some(function_name) = &row.function_name {
        if function_name.starts_with('_') {
            return false;
        }
        let sensor_definition = decorators(program, row.line)
            .iter()
            .any(|name| name.ends_with(SENSOR_DECORATOR_SUFFIX));
        return !has_decorator(program, row.line, allowed_decorators) && !sensor_definition;
    }
    row.class_name
        .as_ref()
        .is_some_and(|name| !name.starts_with('_'))
}

fn assignment_annotation(program: &ProgramHandle, line: u32) -> Option<String> {
    let source = program
        .source()
        .lines()
        .nth(usize::try_from(line.saturating_sub(1)).unwrap_or_default())?;
    let declaration = source.split_once('=').map_or(source, |item| item.0);
    let (_, annotation) = declaration.split_once(':')?;
    Some(
        annotation
            .trim()
            .rsplit('.')
            .next()
            .unwrap_or("")
            .to_owned(),
    )
}

fn invalid_constant_statement(row: &fensu_facts::facts::models::ModuleStatementRow) -> bool {
    if row.import_statement {
        return false;
    }
    for target in &row.assignment_target_names {
        if target.is_empty() || target.chars().any(char::is_lowercase) {
            return true;
        }
    }
    false
}
