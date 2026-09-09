//! Role rules: filenames, directory names, declaration files, helper privacy.

use syn::spanned::Spanned;
use syn::visit::Visit;

use crate::constants;
use crate::models;
use crate::rules::_helpers::imports::reference_paths;
use crate::types::FileKind;

/// Check naming and size rules that apply to every checked file.
pub(crate) fn check_common(
    file: &models::SourceFile,
    thresholds: &models::ThresholdConfig,
) -> Vec<models::Violation> {
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
    if file.line_count() > thresholds.max_file_lines {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSR601",
            path: file.relative_path(),
            line: None,
            message: format!(
                "file has {} lines; the limit is {}",
                file.line_count(),
                thresholds.max_file_lines
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
    thresholds: &models::ThresholdConfig,
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
        violations.extend(check_declaration_budget(file, kind, thresholds));
    }
    if kind == FileKind::BinAdapter {
        violations.extend(check_bin_adapter(file, syntax));
        violations.extend(check_bin_delegation(file, syntax));
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

fn check_declaration_budget(
    file: &models::SourceFile,
    kind: FileKind,
    _thresholds: &models::ThresholdConfig,
) -> Vec<models::Violation> {
    let limit = if kind == FileKind::BinAdapter {
        constants::MAX_BINARY_ENTRY_LINES
    } else {
        constants::MAX_DECLARATION_FILE_LINES
    };
    if file.line_count() <= limit {
        return Vec::new();
    }
    let code = match kind {
        FileKind::BinAdapter => "RSR703",
        _ => "RSR406",
    };
    vec![models::Violation::new(models::ViolationRequest {
        code,
        path: file.relative_path(),
        line: None,
        message: format!(
            "declaration file has {} lines; the limit is {}",
            file.line_count(),
            limit
        ),
        remediation: "keep crate roots as thin declaration surfaces",
    })]
}

#[derive(Default)]
struct MainCallVisitor {
    calls: Vec<(String, usize)>,
    method_lines: Vec<usize>,
}

impl<'ast> Visit<'ast> for MainCallVisitor {
    fn visit_expr_call(&mut self, node: &'ast syn::ExprCall) {
        if let syn::Expr::Path(function) = node.func.as_ref() {
            if let Some(segment) = function.path.segments.last() {
                self.calls
                    .push((segment.ident.to_string(), segment.ident.span().start().line));
            }
        }
        syn::visit::visit_expr_call(self, node);
    }

    fn visit_expr_method_call(&mut self, node: &'ast syn::ExprMethodCall) {
        self.method_lines.push(node.method.span().start().line);
        syn::visit::visit_expr_method_call(self, node);
    }
}

fn check_bin_delegation(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let imported_entries = syntax
        .items
        .iter()
        .filter_map(|item| match item {
            syn::Item::Use(item_use) => Some(reference_paths::use_paths(&item_use.tree)),
            _ => None,
        })
        .flatten()
        .filter(|path| path_crosses_main(path))
        .filter_map(|path| path.last().cloned())
        .collect::<Vec<_>>();
    let Some(main) = syntax.items.iter().find_map(|item| match item {
        syn::Item::Fn(function) if function.sig.ident == constants::MAIN_FUNCTION => Some(function),
        _ => None,
    }) else {
        return Vec::new();
    };
    let mut visitor = MainCallVisitor::default();
    visitor.visit_block(&main.block);
    let delegated = visitor.calls.len() == 1
        && visitor.method_lines.is_empty()
        && visitor
            .calls
            .first()
            .is_some_and(|(name, _)| imported_entries.contains(name));
    if delegated {
        return Vec::new();
    }
    vec![models::Violation::new(models::ViolationRequest {
        code: "RSR702",
        path: file.relative_path(),
        line: Some(main.sig.ident.span().start().line),
        message: "binary main does not delegate exclusively to one imported main/ entry",
        remediation: "move command behavior into a typed main/ entry and call only that entry",
    })]
}

fn path_crosses_main(path: &[String]) -> bool {
    path.iter()
        .any(|segment| segment == constants::MAIN_DIRECTORY)
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
