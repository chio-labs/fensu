//! Test layout rules: harness shape, case-type placement, topic-file content.

use syn::spanned::Spanned;

use crate::constants;
use crate::models;
use crate::types::FileKind;

/// Check that every test area mirrors a source area of the same crate.
pub(crate) fn check_test_mirroring(
    repo_root: &std::path::Path,
    crate_dir: &std::path::Path,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let tests_root = crate_dir.join(constants::TESTS_DIRECTORY);
    let src_root = crate_dir.join(constants::SOURCE_DIRECTORY);
    if !tests_root.exists() {
        return violations;
    }
    let entries = match std::fs::read_dir(&tests_root) {
        Ok(entries) => entries,
        Err(error) => {
            let relative = tests_root.strip_prefix(repo_root).unwrap_or(&tests_root);
            return vec![models::Violation::new(
                "RSH901",
                relative,
                None,
                format!("cannot read Rust test directory: {error}"),
                "restore a readable test directory before checking structure",
            )];
        }
    };
    let mut area_names: Vec<String> = Vec::new();
    for result in entries {
        match result {
            Ok(entry) if entry.path().is_dir() => {
                let name = entry.file_name().to_string_lossy().into_owned();
                area_names.push(name);
            }
            Ok(_) => {}
            Err(error) => violations.push(models::Violation::new(
                "RSH901",
                tests_root.strip_prefix(repo_root).unwrap_or(&tests_root),
                None,
                format!("cannot inspect Rust test directory entry: {error}"),
                "restore a readable test directory before checking structure",
            )),
        }
    }
    area_names.sort();
    for name in &area_names {
        let mirrors_directory = src_root.join(name).is_dir();
        let mirrors_module = src_root.join(format!("{name}.rs")).is_file();
        if mirrors_directory || mirrors_module {
            continue;
        }
        let area = tests_root.join(name);
        let relative = area.strip_prefix(repo_root).unwrap_or(&area);
        violations.push(models::Violation::new(
            "RST003",
            relative,
            None,
            format!("test area {name} mirrors no source area"),
            "name test areas after the src module or domain they exercise",
        ));
    }
    violations
}

/// Check layout rules for one test file according to its role.
pub(crate) fn check(
    file: &models::SourceFile,
    syntax: &syn::File,
    kind: FileKind,
) -> Vec<models::Violation> {
    match kind {
        FileKind::TestHarness => check_harness(file, syntax),
        FileKind::TestTypes => check_test_types(file, syntax),
        FileKind::TestHelpers => check_struct_placement(file, syntax),
        FileKind::TestTopic => check_topic(file, syntax),
        _ => Vec::new(),
    }
}

fn check_harness(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for item in &syntax.items {
        let syn::Item::Mod(item_mod) = item else {
            violations.push(models::Violation::new(
                "RST101",
                file.relative_path(),
                Some(item.span().start().line),
                "test harness files may contain module declarations only",
                "declare #[path] modules here and put content in the area folder",
            ));
            continue;
        };
        let has_path_attribute = item_mod
            .attrs
            .iter()
            .any(|attribute| attribute.path().is_ident("path"));
        if item_mod.content.is_some() || !has_path_attribute {
            violations.push(models::Violation::new(
                "RST101",
                file.relative_path(),
                Some(item_mod.ident.span().start().line),
                "harness modules must be #[path] declarations without bodies",
                "declare #[path = \"<area>/<file>.rs\"] mod <file>; only",
            ));
        }
    }
    violations
}

fn check_test_types(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for item in &syntax.items {
        let syn::Item::Struct(item_struct) = item else {
            continue;
        };
        let name = item_struct.ident.to_string();
        if !name.ends_with(constants::TEST_CASE_STRUCT_SUFFIX) {
            continue;
        }
        let field_names: Vec<String> = struct_field_names(item_struct);
        let line = Some(item_struct.ident.span().start().line);
        if !field_names
            .iter()
            .any(|f| f == constants::DESCRIPTION_FIELD)
        {
            violations.push(models::Violation::new(
                "RST201",
                file.relative_path(),
                line,
                format!("{name} lacks a description field"),
                "add description: &'static str so failures explain the behavior",
            ));
        }
        let has_expected = field_names
            .iter()
            .any(|f| f.starts_with(constants::EXPECTED_FIELD_PREFIX));
        if !has_expected {
            violations.push(models::Violation::new(
                "RST202",
                file.relative_path(),
                line,
                format!("{name} lacks an expected_ field"),
                "name expected outcomes with an expected_ prefix and assert against them",
            ));
        }
    }
    violations
}

fn check_topic(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut violations = check_struct_placement(file, syntax);
    let mut seen_function = false;
    for item in &syntax.items {
        match item {
            syn::Item::Fn(item_fn) => {
                seen_function = true;
                if !has_test_attribute(item_fn) {
                    violations.push(models::Violation::new(
                        "RST103",
                        file.relative_path(),
                        Some(item_fn.sig.ident.span().start().line),
                        format!("{} is not a test function", item_fn.sig.ident),
                        "move shared functions into the area's helpers.rs",
                    ));
                }
            }
            syn::Item::Const(item_const) => {
                violations.extend(check_topic_const(file, item_const, seen_function));
            }
            _ => {}
        }
    }
    violations
}

fn check_topic_const(
    file: &models::SourceFile,
    item_const: &syn::ItemConst,
    seen_function: bool,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let line = Some(item_const.ident.span().start().line);
    if item_const.ident == constants::MODULE_CASES_CONSTANT {
        violations.push(models::Violation::new(
            "RST401",
            file.relative_path(),
            line,
            "module-level TEST_CASES arrays hide cases from their test",
            "declare let test_cases = [ ... ]; inside the test function",
        ));
    }
    if seen_function {
        violations.push(models::Violation::new(
            "RST105",
            file.relative_path(),
            line,
            "constant declared after the first test function",
            "move constants above the tests so setup is visible first",
        ));
    }
    violations
}

fn check_struct_placement(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for item in &syntax.items {
        if let syn::Item::Struct(item_struct) = item {
            violations.push(models::Violation::new(
                "RST203",
                file.relative_path(),
                Some(item_struct.ident.span().start().line),
                format!(
                    "struct {} declared outside test_types.rs",
                    item_struct.ident
                ),
                "move test-case and fixture structs into the area's test_types.rs",
            ));
        }
    }
    violations
}

fn struct_field_names(item_struct: &syn::ItemStruct) -> Vec<String> {
    item_struct
        .fields
        .iter()
        .filter_map(|field| field.ident.as_ref().map(|ident| ident.to_string()))
        .collect()
}

fn has_test_attribute(item_fn: &syn::ItemFn) -> bool {
    item_fn
        .attrs
        .iter()
        .any(|attribute| attribute.path().is_ident("test"))
}
