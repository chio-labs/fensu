//! Role rules: filenames, directory names, declaration files, helper privacy.

use syn::spanned::Spanned;

use crate::constants;
use crate::models;
use crate::types::FileKind;

/// Check naming and size rules that apply to every checked file.
pub(crate) fn check_common(file: &models::SourceFile) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    if constants::BANNED_FILE_STEMS.contains(&file.file_stem()) {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSR201",
            path: file.relative_path(),
            line: None,
            message: format!("uses banned generic filename {}", file.file_name()),
            remediation: "name the module after the capability it owns",
        }));
    }
    if file.file_name() == constants::HELPERS_FILE && !file.relative.contains("/tests/") {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSR202",
            path: file.relative_path(),
            line: None,
            message: "helpers.rs is banned",
            remediation: "use an _helpers/ directory of specifically named modules",
        }));
    }
    for banned in constants::BANNED_DIRECTORY_NAMES {
        if file.has_directory(banned) {
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RSR204",
                path: file.relative_path(),
                line: None,
                message: format!("is under banned generic directory {banned}"),
                remediation: "name the directory after the capability it owns",
            }));
        }
    }
    if file.line_count() > constants::MAX_FILE_LINES {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSR601",
            path: file.relative_path(),
            line: None,
            message: format!(
                "file has {} lines; the limit is {}",
                file.line_count(),
                constants::MAX_FILE_LINES
            ),
            remediation: "split the file by a cohesive concern",
        }));
    }
    violations
}

/// Check role and shape rules for one library source file.
pub(crate) fn check_source(
    file: &models::SourceFile,
    syntax: &syn::File,
    kind: FileKind,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    if file.has_directory(constants::HELPERS_DIRECTORY) && file.file_name() == constants::MAIN_FILE
    {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSR502",
            path: file.relative_path(),
            line: None,
            message: "helpers/ must not contain main.rs",
            remediation: "move orchestration into the crate's entry modules",
        }));
    }
    for item in &syntax.items {
        violations.extend(check_item(file, item, kind));
    }
    if kind == FileKind::LibraryRoot || kind == FileKind::BinAdapter {
        violations.extend(check_declaration_budget(file, kind));
    }
    if kind == FileKind::BinAdapter {
        violations.extend(check_bin_adapter(file, syntax));
    }
    if kind == FileKind::ModuleFile {
        violations.extend(check_declaration_order(file, syntax));
    }
    violations
}

fn check_declaration_order(
    file: &models::SourceFile,
    syntax: &syn::File,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let mut seen_function = false;
    for item in &syntax.items {
        if matches!(item, syn::Item::Fn(_)) {
            seen_function = true;
        }
        let declaration = matches!(item, syn::Item::Const(_) | syn::Item::Static(_));
        if declaration && seen_function {
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RSR503",
                path: file.relative_path(),
                line: item_line(item),
                message: "constant declared after the first function",
                remediation: "move module state above behavior so readers see it first",
            }));
        }
    }
    violations
}

fn check_item(
    file: &models::SourceFile,
    item: &syn::Item,
    kind: FileKind,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    if let syn::Item::Mod(item_mod) = item {
        if item_mod.content.is_some() {
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RST001",
                path: file.relative_path(),
                line: Some(item_mod.ident.span().start().line),
                message: format!("inline module {} has a body", item_mod.ident),
                remediation: "move modules to their own files and tests under tests/",
            }));
        }
    }
    if let syn::Item::Use(item_use) = item {
        violations.extend(check_use_visibility(file, item_use, kind));
    }
    if (kind == FileKind::ModRoot || kind == FileKind::LibraryRoot)
        && !matches!(item, syn::Item::Mod(_) | syn::Item::Use(_))
    {
        let code = match kind {
            FileKind::ModRoot => "RSR402",
            _ => "RSR406",
        };
        violations.push(models::Violation::new(models::ViolationRequest {
            code,
            path: file.relative_path(),
            line: item_line(item),
            message: "declaration files must contain module declarations only",
            remediation: "move implementation items into their owning modules",
        }));
    }
    if file.has_directory(constants::HELPERS_DIRECTORY) {
        violations.extend(check_helper_visibility(file, item));
    }
    violations
}

fn check_use_visibility(
    file: &models::SourceFile,
    item_use: &syn::ItemUse,
    kind: FileKind,
) -> Vec<models::Violation> {
    if file.has_directory(constants::HELPERS_DIRECTORY)
        && !matches!(item_use.vis, syn::Visibility::Inherited)
    {
        return vec![models::Violation::new(models::ViolationRequest {
            code: "RSR404",
            path: file.relative_path(),
            line: Some(item_use.use_token.span.start().line),
            message: "_helpers module publishes a re-export",
            remediation:
                "keep _helpers internal and expose behavior through a main entry or role file",
        })];
    }
    match &item_use.vis {
        syn::Visibility::Public(_) if kind != FileKind::LibraryRoot => {
            vec![models::Violation::new(models::ViolationRequest {
                code: "RSR403",
                path: file.relative_path(),
                line: Some(item_use.use_token.span.start().line),
                message: "pub use re-export outside the crate root",
                remediation: "re-export only from lib.rs; import the concrete module elsewhere",
            })]
        }
        syn::Visibility::Restricted(_) => vec![models::Violation::new(models::ViolationRequest {
            code: "RSR403",
            path: file.relative_path(),
            line: Some(item_use.use_token.span.start().line),
            message: "scoped pub use re-exports are banned",
            remediation: "import the owning module explicitly instead of re-exporting",
        })],
        _ => Vec::new(),
    }
}

fn check_helper_visibility(file: &models::SourceFile, item: &syn::Item) -> Vec<models::Violation> {
    if matches!(item, syn::Item::Mod(_)) {
        return Vec::new();
    }
    let Some(visibility) = item_visibility(item) else {
        return Vec::new();
    };
    if !matches!(visibility, syn::Visibility::Public(_)) {
        return Vec::new();
    }
    vec![models::Violation::new(models::ViolationRequest {
        code: "RSR205",
        path: file.relative_path(),
        line: item_line(item),
        message: "helpers/ exposes a fully public item",
        remediation:
            "keep helper items crate-visible at most; domain boundaries are enforced on imports",
    })]
}

fn check_declaration_budget(file: &models::SourceFile, kind: FileKind) -> Vec<models::Violation> {
    if file.line_count() <= constants::MAX_DECLARATION_FILE_LINES {
        return Vec::new();
    }
    let code = match kind {
        FileKind::BinAdapter => "RSR701",
        _ => "RSR406",
    };
    vec![models::Violation::new(models::ViolationRequest {
        code,
        path: file.relative_path(),
        line: None,
        message: format!(
            "declaration file has {} lines; the limit is {}",
            file.line_count(),
            constants::MAX_DECLARATION_FILE_LINES
        ),
        remediation: "keep crate roots as thin declaration surfaces",
    })]
}

fn check_bin_adapter(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let mut function_count: usize = 0;
    for item in &syntax.items {
        match item {
            syn::Item::Fn(_) => function_count += 1,
            syn::Item::Use(_) => {}
            other => violations.push(models::Violation::new(models::ViolationRequest {
                code: "RSR701",
                path: file.relative_path(),
                line: item_line(other),
                message: "bin adapters may contain only imports and one main function",
                remediation: "move implementation into the library crate",
            })),
        }
    }
    if function_count != 1 {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSR701",
            path: file.relative_path(),
            line: None,
            message: format!("bin adapter defines {function_count} functions"),
            remediation: "keep exactly one main function delegating to the library",
        }));
    }
    violations
}

fn item_visibility(item: &syn::Item) -> Option<&syn::Visibility> {
    match item {
        syn::Item::Const(inner) => Some(&inner.vis),
        syn::Item::Enum(inner) => Some(&inner.vis),
        syn::Item::Fn(inner) => Some(&inner.vis),
        syn::Item::Mod(inner) => Some(&inner.vis),
        syn::Item::Static(inner) => Some(&inner.vis),
        syn::Item::Struct(inner) => Some(&inner.vis),
        syn::Item::Trait(inner) => Some(&inner.vis),
        syn::Item::Type(inner) => Some(&inner.vis),
        _ => None,
    }
}

fn item_line(item: &syn::Item) -> Option<usize> {
    Some(item.span().start().line)
}
