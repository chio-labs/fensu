//! Role-file content and placement rules for models, types, constants, errors.

use syn::spanned::Spanned;

use crate::constants;
use crate::models;
use crate::types::FileKind;

pub(crate) fn check(
    file: &models::SourceFile,
    syntax: &syn::File,
    kind: FileKind,
) -> Vec<models::Violation> {
    if kind == FileKind::LibraryRoot || kind == FileKind::BinAdapter {
        return Vec::new();
    }
    let mut violations = check_role_content(file, syntax);
    violations.extend(check_placement(file, syntax));
    violations
}

fn check_role_content(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for item in &syntax.items {
        violations.extend(role_content_violation(file, item));
        if file.file_name() == constants::MODELS_FILE {
            violations.extend(check_model_derives(file, item));
        }
    }
    violations
}

fn role_content_violation(file: &models::SourceFile, item: &syn::Item) -> Vec<models::Violation> {
    let allowed = match file.file_name() {
        name if name == constants::MODELS_FILE || name == constants::ERRORS_FILE => matches!(
            item,
            syn::Item::Struct(_) | syn::Item::Enum(_) | syn::Item::Impl(_) | syn::Item::Use(_)
        ),
        name if name == constants::TYPES_FILE => matches!(
            item,
            syn::Item::Enum(_) | syn::Item::Trait(_) | syn::Item::Type(_) | syn::Item::Use(_)
        ),
        name if name == constants::CONSTANTS_FILE => {
            matches!(item, syn::Item::Const(_) | syn::Item::Use(_))
        }
        _ => true,
    };
    if allowed {
        return Vec::new();
    }
    let (code, role) = match file.file_name() {
        name if name == constants::TYPES_FILE => ("RSR002", "types.rs"),
        name if name == constants::CONSTANTS_FILE => ("RSR003", "constants.rs"),
        name if name == constants::ERRORS_FILE => ("RSR004", "errors.rs"),
        _ => ("RSR001", "models.rs"),
    };
    vec![models::Violation::new(
        code,
        file.relative_path(),
        Some(item.span().start().line),
        format!("{role} contains an item outside its role"),
        "move the item into the module role that owns it",
    )]
}

fn check_model_derives(file: &models::SourceFile, item: &syn::Item) -> Vec<models::Violation> {
    let syn::Item::Struct(item_struct) = item else {
        return Vec::new();
    };
    if derives_debug(&item_struct.attrs) {
        return Vec::new();
    }
    vec![models::Violation::new(
        "RSS201",
        file.relative_path(),
        Some(item_struct.ident.span().start().line),
        format!("model {} does not derive Debug", item_struct.ident),
        "derive Debug on every data model for diagnosability",
    )]
}

fn derives_debug(attributes: &[syn::Attribute]) -> bool {
    attributes.iter().any(|attribute| {
        let is_derive = attribute.path().is_ident("derive");
        let names = match &attribute.meta {
            syn::Meta::List(list) => list.tokens.to_string(),
            _ => String::new(),
        };
        is_derive && names.contains(constants::DEBUG_DERIVE)
    })
}

fn check_placement(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let name = file.file_name();
    for item in &syntax.items {
        violations.extend(data_struct_violation(file, item, name));
        violations.extend(type_layer_violation(file, item, name));
        violations.extend(constant_violation(file, item, name));
        violations.extend(error_type_violation(file, item, name));
    }
    violations
}

fn data_struct_violation(
    file: &models::SourceFile,
    item: &syn::Item,
    name: &str,
) -> Vec<models::Violation> {
    let data_roles = [
        constants::MODELS_FILE,
        constants::TYPES_FILE,
        constants::ERRORS_FILE,
    ];
    if data_roles.contains(&name) {
        return Vec::new();
    }
    let syn::Item::Struct(item_struct) = item else {
        return Vec::new();
    };
    if !matches!(item_struct.vis, syn::Visibility::Public(_)) {
        return Vec::new();
    }
    let has_public_field = item_struct
        .fields
        .iter()
        .any(|field| matches!(field.vis, syn::Visibility::Public(_)));
    if !has_public_field {
        return Vec::new();
    }
    vec![models::Violation::new(
        "RSR101",
        file.relative_path(),
        Some(item_struct.ident.span().start().line),
        format!("public data struct {} outside models.rs", item_struct.ident),
        "move shared data carriers into the owning models.rs",
    )]
}

fn type_layer_violation(
    file: &models::SourceFile,
    item: &syn::Item,
    name: &str,
) -> Vec<models::Violation> {
    if name == constants::TYPES_FILE {
        return Vec::new();
    }
    let declaration = match item {
        syn::Item::Trait(inner) if matches!(inner.vis, syn::Visibility::Public(_)) => {
            Some(inner.ident.span().start().line)
        }
        syn::Item::Type(inner) if matches!(inner.vis, syn::Visibility::Public(_)) => {
            Some(inner.ident.span().start().line)
        }
        _ => None,
    };
    let Some(line) = declaration else {
        return Vec::new();
    };
    vec![models::Violation::new(
        "RSR102",
        file.relative_path(),
        Some(line),
        "public type-layer declaration outside types.rs",
        "move public traits and type aliases into the owning types.rs",
    )]
}

fn constant_violation(
    file: &models::SourceFile,
    item: &syn::Item,
    name: &str,
) -> Vec<models::Violation> {
    if name == constants::CONSTANTS_FILE {
        return Vec::new();
    }
    let syn::Item::Const(item_const) = item else {
        return Vec::new();
    };
    if !matches!(item_const.vis, syn::Visibility::Public(_)) {
        return Vec::new();
    }
    vec![models::Violation::new(
        "RSR103",
        file.relative_path(),
        Some(item_const.ident.span().start().line),
        format!("public constant {} outside constants.rs", item_const.ident),
        "move public constants into the owning constants.rs",
    )]
}

fn error_type_violation(
    file: &models::SourceFile,
    item: &syn::Item,
    name: &str,
) -> Vec<models::Violation> {
    if name == constants::ERRORS_FILE {
        return Vec::new();
    }
    let declaration = match item {
        syn::Item::Struct(inner) => Some((&inner.ident, inner.ident.span().start().line)),
        syn::Item::Enum(inner) => Some((&inner.ident, inner.ident.span().start().line)),
        _ => None,
    };
    let Some((ident, line)) = declaration else {
        return Vec::new();
    };
    if !ident.to_string().ends_with(constants::ERROR_TYPE_SUFFIX) {
        return Vec::new();
    }
    vec![models::Violation::new(
        "RSR104",
        file.relative_path(),
        Some(line),
        format!("error type {ident} outside errors.rs"),
        "define error types in the owning errors.rs",
    )]
}
