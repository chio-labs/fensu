//! Role rules: filenames, directory names, declaration files, helper privacy.

use syn::spanned::Spanned;

use crate::constants;
use crate::models;
use crate::types::FileKind;

/// Check naming and size rules that apply to every checked file.
pub(crate) fn check_common(file: &models::SourceFile) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    if constants::BANNED_FILE_STEMS.contains(&file.file_stem()) {
        violations.push(models::Violation::new(
            "RSR201",
            file.relative_path(),
            None,
            format!("uses banned generic filename {}", file.file_name()),
            "name the module after the capability it owns",
        ));
    }
    if file.file_name() == constants::HELPERS_FILE && !file.relative.contains("/tests/") {
        violations.push(models::Violation::new(
            "RSR202",
            file.relative_path(),
            None,
            "helpers.rs is banned",
            "use a helpers/ directory of specifically named modules",
        ));
    }
    for banned in constants::BANNED_DIRECTORY_NAMES {
        if file.has_directory(banned) {
            violations.push(models::Violation::new(
                "RSR204",
                file.relative_path(),
                None,
                format!("is under banned generic directory {banned}"),
                "name the directory after the capability it owns",
            ));
        }
    }
    if file.line_count() > constants::MAX_FILE_LINES {
        violations.push(models::Violation::new(
            "RSR601",
            file.relative_path(),
            None,
            format!(
                "file has {} lines; the limit is {}",
                file.line_count(),
                constants::MAX_FILE_LINES
            ),
            "split the file by a cohesive concern",
        ));
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
        violations.push(models::Violation::new(
            "RSR502",
            file.relative_path(),
            None,
            "helpers/ must not contain main.rs",
            "move orchestration into the crate's entry modules",
        ));
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
            violations.push(models::Violation::new(
                "RSR503",
                file.relative_path(),
                item_line(item),
                "constant declared after the first function",
                "move module state above behavior so readers see it first",
            ));
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
            violations.push(models::Violation::new(
                "RST001",
                file.relative_path(),
                Some(item_mod.ident.span().start().line),
                format!("inline module {} has a body", item_mod.ident),
                "move modules to their own files and tests under tests/",
            ));
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
        violations.push(models::Violation::new(
            code,
            file.relative_path(),
            item_line(item),
            "declaration files must contain module declarations only",
            "move implementation items into their owning modules",
        ));
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
    match &item_use.vis {
        syn::Visibility::Public(_) if kind != FileKind::LibraryRoot => {
            vec![models::Violation::new(
                "RSR403",
                file.relative_path(),
                Some(item_use.use_token.span.start().line),
                "pub use re-export outside the crate root",
                "re-export only from lib.rs; import the concrete module elsewhere",
            )]
        }
        syn::Visibility::Restricted(_) => vec![models::Violation::new(
            "RSR403",
            file.relative_path(),
            Some(item_use.use_token.span.start().line),
            "scoped pub use re-exports are banned",
            "import the owning module explicitly instead of re-exporting",
        )],
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
    vec![models::Violation::new(
        "RSR205",
        file.relative_path(),
        item_line(item),
        "helpers/ exposes a fully public item",
        "keep helper items crate-visible at most; domain boundaries are enforced on imports",
    )]
}

fn check_declaration_budget(file: &models::SourceFile, kind: FileKind) -> Vec<models::Violation> {
    if file.line_count() <= constants::MAX_DECLARATION_FILE_LINES {
        return Vec::new();
    }
    let code = match kind {
        FileKind::BinAdapter => "RSR701",
        _ => "RSR406",
    };
    vec![models::Violation::new(
        code,
        file.relative_path(),
        None,
        format!(
            "declaration file has {} lines; the limit is {}",
            file.line_count(),
            constants::MAX_DECLARATION_FILE_LINES
        ),
        "keep crate roots as thin declaration surfaces",
    )]
}

fn check_bin_adapter(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let mut function_count: usize = 0;
    for item in &syntax.items {
        match item {
            syn::Item::Fn(_) => function_count += 1,
            syn::Item::Use(_) => {}
            other => violations.push(models::Violation::new(
                "RSR701",
                file.relative_path(),
                item_line(other),
                "bin adapters may contain only imports and one main function",
                "move implementation into the library crate",
            )),
        }
    }
    if function_count != 1 {
        violations.push(models::Violation::new(
            "RSR701",
            file.relative_path(),
            None,
            format!("bin adapter defines {function_count} functions"),
            "keep exactly one main function delegating to the library",
        ));
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
