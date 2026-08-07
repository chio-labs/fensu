use fensu_facts::extension::models::ProgramHandle;
use fensu_facts::facts::models::ImportRow;

use crate::rules::_helpers::dagster::{
    asset_callbacks, factory_backed_assets, fault, file_name, function_source, has_decorator,
    in_definition_role, module_name, path_fault, positional_parameter_names, signature_source,
    top_level_functions, ASSET_DECORATORS, AUTOMATION_ROLES, PRIVATE_ROLE_FILES,
};
use crate::rules::models::{NativeFaultRow, NativeProjectPlane, NativeRuleContext};

const ASSETS_BINDING: &str = "assets";
const ASSETS_FILE: &str = "assets.py";
const HELPERS_ROLE: &str = "_helpers";
const LEGACY_ASSETS_FILE: &str = "pipeline_assets.py";
const LEGACY_CONSTANTS_FILE: &str = "pipeline_constants.py";
const MAIN_FILE: &str = "main.py";
const MAIN_FUNCTION: &str = "main";

pub(super) fn asset_package_layout(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
    project: &NativeProjectPlane,
) -> Vec<NativeFaultRow> {
    if matches!(
        file_name(context),
        LEGACY_ASSETS_FILE | LEGACY_CONSTANTS_FILE
    ) {
        return vec![path_fault(code, None)];
    }
    if file_name(context) != ASSETS_FILE || factory_backed_assets(program) {
        return Vec::new();
    }
    let sibling = context.repository_path.rsplit_once('/').map_or_else(
        || MAIN_FILE.to_owned(),
        |(parent, _)| format!("{parent}/{MAIN_FILE}"),
    );
    if project.modules.iter().any(|module| module.path == sibling) {
        Vec::new()
    } else {
        vec![path_fault(code, None)]
    }
}

pub(super) fn assets_module_shape(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    if file_name(context) != ASSETS_FILE {
        return Vec::new();
    }
    if factory_backed_assets(program) {
        return program
            .declaration_rows()
            .statements
            .iter()
            .filter(|row| non_asset_factory_statement(row))
            .map(|row| fault(code, row.line, row.column))
            .collect();
    }
    let top_level = top_level_functions(program);
    let public: Vec<_> = top_level
        .iter()
        .filter(|row| !row.name.starts_with('_'))
        .copied()
        .collect();
    let mut faults: Vec<NativeFaultRow> = top_level
        .iter()
        .filter(|row| row.name.starts_with('_'))
        .map(|row| fault(code, row.line, row.column))
        .collect();
    if public.len() != 1 {
        faults.push(path_fault(code, None));
        return faults;
    }
    let candidate = public[0];
    let decorated = has_decorator(program, candidate.line, ASSET_DECORATORS);
    let nested_asset = asset_callbacks(program).iter().any(|callback| {
        callback.line > candidate.line
            && function_source(program, candidate.line).contains(&format!("def {}", callback.name))
    });
    if !decorated && !nested_asset {
        faults.push(fault(code, candidate.line, candidate.column));
    }
    faults
}

fn imports_sibling_main(program: &ProgramHandle, context: &NativeRuleContext) -> bool {
    let expected = format!(
        "{}.main",
        module_name(context)
            .rsplit_once('.')
            .map_or("", |item| item.0)
    );
    program
        .reference_rows()
        .imports
        .iter()
        .any(|row| imports_expected_main(row, &expected))
}

fn non_asset_factory_statement(row: &fensu_facts::facts::models::ModuleStatementRow) -> bool {
    !row.import_statement
        && !row
            .assignment_target_names
            .iter()
            .any(|name| name == ASSETS_BINDING)
}

fn imports_expected_main(row: &ImportRow, expected: &str) -> bool {
    let imports_main = row
        .aliases
        .iter()
        .any(|alias| alias.imported_name == MAIN_FUNCTION && alias.bound_name == MAIN_FUNCTION);
    row.from_import
        && row.relative_level == 0
        && row.module_parts.join(".") == expected
        && imports_main
}

pub(super) fn assets_delegate_to_main(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    if file_name(context) != ASSETS_FILE || factory_backed_assets(program) {
        return Vec::new();
    }
    let callbacks = asset_callbacks(program);
    let mut faults: Vec<NativeFaultRow> = Vec::new();
    if !imports_sibling_main(program, context) || callbacks.is_empty() {
        faults.push(path_fault(code, None));
    }
    for callback in callbacks {
        let body = function_source(program, callback.line);
        let direct = body
            .lines()
            .skip(1)
            .filter(|line| !line.trim().is_empty())
            .collect::<Vec<_>>();
        let valid = direct.len() == 1
            && (direct[0].trim_start().starts_with("return main(")
                || direct[0].trim_start().starts_with("yield from main("));
        if !valid {
            faults.push(fault(code, callback.line, callback.column));
        }
    }
    faults
}

fn approved_main_return(signature: &str) -> bool {
    signature.contains("MaterializeResult")
        || signature.contains("Iterator[")
        || signature.contains("Generator[")
        || signature.contains("NoReturn")
        || signature.contains("Never")
}

pub(super) fn main_module_shape(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
    project: &NativeProjectPlane,
) -> Vec<NativeFaultRow> {
    if file_name(context) != MAIN_FILE {
        return Vec::new();
    }
    let sibling = context
        .repository_path
        .trim_end_matches(MAIN_FILE)
        .to_owned()
        + ASSETS_FILE;
    if !project.modules.iter().any(|module| module.path == sibling) {
        return Vec::new();
    }
    let functions = top_level_functions(program);
    let mains: Vec<_> = functions
        .iter()
        .filter(|row| row.name == MAIN_FUNCTION)
        .copied()
        .collect();
    let mut faults: Vec<NativeFaultRow> = program
        .declaration_rows()
        .statements
        .iter()
        .filter(|row| {
            !row.import_statement
                && row.function_name.as_deref() != Some(MAIN_FUNCTION)
                && !row.docstring_statement
        })
        .map(|row| fault(code, row.line, row.column))
        .collect();
    if mains.len() != 1 {
        faults.push(path_fault(code, None));
    }
    for main in mains {
        if !approved_main_return(&signature_source(program, main.line)) {
            faults.push(fault(code, main.line, main.column));
        }
        for nested in &program.function_rows().0 {
            if nested.line > main.line
                && !functions
                    .iter()
                    .any(|candidate| candidate.line == nested.line)
                && function_source(program, main.line).contains(&format!("def {}", nested.name))
            {
                faults.push(fault(code, nested.line, nested.column));
            }
        }
    }
    faults
}

pub(super) fn asset_callback_signature(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    if file_name(context) != ASSETS_FILE {
        return Vec::new();
    }
    asset_callbacks(program)
        .into_iter()
        .filter(|row| positional_parameter_names(program, row.line) != ["context"])
        .map(|row| fault(code, row.line, row.column))
        .collect()
}

pub(super) fn import_target(row: &ImportRow) -> Vec<String> {
    if row.from_import {
        vec![row.module_parts.join(".")]
    } else {
        row.aliases
            .iter()
            .map(|alias| alias.imported_name.clone())
            .collect()
    }
}

fn import_public(row: &ImportRow) -> bool {
    row.aliases
        .iter()
        .all(|alias| !alias.bound_name.starts_with('_'))
}

fn nearest_asset_owner(
    context: &NativeRuleContext,
    project: &NativeProjectPlane,
) -> Option<String> {
    let parent = context
        .repository_path
        .rsplit_once('/')
        .map_or("", |item| item.0);
    let mut candidate = parent;
    loop {
        let marker = format!("{candidate}/{ASSETS_FILE}");
        if project.modules.iter().any(|module| module.path == marker) {
            return Some(candidate.replace('/', "."));
        }
        let (next, _) = candidate.rsplit_once('/')?;
        candidate = next;
    }
}

pub(super) fn import_boundaries(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
    project: &NativeProjectPlane,
) -> Vec<NativeFaultRow> {
    if !in_definition_role(context, "assets") {
        return Vec::new();
    }
    let Some(owner) = nearest_asset_owner(context, project) else {
        return Vec::new();
    };
    let package = &context.package_name;
    let mut faults: Vec<NativeFaultRow> = Vec::new();
    for row in &program.reference_rows().imports {
        for target in import_target(row) {
            if target != *package && !target.starts_with(&format!("{package}.")) {
                continue;
            }
            let private = target.split('.').skip(1).any(|part| part.starts_with('_'));
            let shared = (target.starts_with(&format!("{package}.defs.resources."))
                || target.starts_with(&format!("{package}.resources."))
                || target == format!("{package}.utils")
                || target.starts_with(&format!("{package}.utils.")))
                && !private
                && import_public(row);
            let owned = target == format!("{owner}.main")
                || target.starts_with(&format!("{owner}._helpers."))
                || ["constants", "exceptions", "models", "types"]
                    .iter()
                    .any(|role| target == format!("{owner}.{role}"));
            let dependency = row.from_import && target.ends_with(".assets");
            if !shared && !owned && !dependency {
                faults.push(fault(code, row.line, row.column));
                break;
            }
        }
    }
    faults
}

pub(super) fn role_parts(context: &NativeRuleContext) -> Option<(&str, &[String])> {
    let parts = &context.relative_parts;
    if parts.first().map(String::as_str) != Some("defs")
        || !parts
            .get(1)
            .is_some_and(|part| AUTOMATION_ROLES.contains(&part.as_str()))
    {
        return None;
    }
    Some((parts[1].as_str(), &parts[2..]))
}

pub(super) fn private_definition_support(context: &NativeRuleContext) -> bool {
    PRIVATE_ROLE_FILES.contains(&file_name(context))
        || context
            .relative_parts
            .iter()
            .any(|part| part == HELPERS_ROLE)
}
