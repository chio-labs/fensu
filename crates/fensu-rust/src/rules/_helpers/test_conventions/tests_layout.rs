//! Per-file test layout rules: harness shape, case-type placement, topic-file content.

use syn::spanned::Spanned;

use crate::constants;
use crate::models;
use crate::types::FileKind;

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

/// Report test functions declared outside integration or inline unit-test scopes.
pub(crate) fn check_source_scope(
    file: &models::SourceFile,
    syntax: &syn::File,
) -> Vec<models::Violation> {
    syntax
        .items
        .iter()
        .filter_map(|item| match item {
            syn::Item::Fn(function) if has_test_attribute(function) => Some(function),
            _ => None,
        })
        .map(|function| {
            models::Violation::new(models::ViolationRequest {
                code: "RST002",
                path: file.relative_path(),
                line: Some(function.sig.ident.span().start().line),
                message: "test function is outside a recognized Rust test scope",
                remediation: "move it under tests/<area>/ or src/<domain>/tests/",
            })
        })
        .collect()
}

fn check_harness(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for item in &syntax.items {
        let syn::Item::Mod(item_mod) = item else {
            if matches!(item, syn::Item::Fn(function) if has_test_attribute(function)) {
                violations.push(models::Violation::new(models::ViolationRequest {
                    code: "RST004",
                    path: file.relative_path(),
                    line: Some(item.span().start().line),
                    message: "runtime test is not nested beneath a source area",
                    remediation:
                        "move the test into tests/<source-area>/ and declare it from a harness",
                }));
            }
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RST101",
                path: file.relative_path(),
                line: Some(item.span().start().line),
                message: "test harness files may contain module declarations only",
                remediation: "declare #[path] modules here and put content in the area folder",
            }));
            continue;
        };
        let has_path_attribute = item_mod
            .attrs
            .iter()
            .any(|attribute| attribute.path().is_ident("path"));
        if item_mod.content.is_some() || !has_path_attribute {
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RST101",
                path: file.relative_path(),
                line: Some(item_mod.ident.span().start().line),
                message: "harness modules must be #[path] declarations without bodies",
                remediation: "declare #[path = \"<area>/<file>.rs\"] mod <file>; only",
            }));
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
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RST201",
                path: file.relative_path(),
                line,
                message: format!("{name} lacks a description field"),
                remediation: "add description: &'static str so failures explain the behavior",
            }));
        }
        let has_expected = field_names
            .iter()
            .any(|f| f.starts_with(constants::EXPECTED_FIELD_PREFIX));
        if !has_expected {
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RST202",
                path: file.relative_path(),
                line,
                message: format!("{name} lacks an expected_ field"),
                remediation:
                    "name expected outcomes with an expected_ prefix and assert against them",
            }));
        }
    }
    violations
}

fn check_topic(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut violations = check_struct_placement(file, syntax);
    violations.extend(check_topic_file_contract(file, syntax));
    let mut seen_function = false;
    for item in &syntax.items {
        match item {
            syn::Item::Fn(item_fn) => {
                seen_function = true;
                if !has_test_attribute(item_fn) {
                    violations.push(models::Violation::new(models::ViolationRequest {
                        code: "RST103",
                        path: file.relative_path(),
                        line: Some(item_fn.sig.ident.span().start().line),
                        message: format!("{} is not a test function", item_fn.sig.ident),
                        remediation: "move shared functions into the area's helpers.rs",
                    }));
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

fn check_topic_file_contract(
    file: &models::SourceFile,
    syntax: &syn::File,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    if !file.file_stem().starts_with(constants::TEST_FILE_PREFIX) {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST301",
            path: file.relative_path(),
            line: None,
            message: "test topic filename does not start with test_",
            remediation: "rename the module to test_<behavior>.rs",
        }));
    }
    let test_types = file.path.with_file_name(constants::TEST_TYPES_FILE);
    if !test_types.is_file() {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST204",
            path: file.relative_path(),
            line: None,
            message: "test topic has no sibling test_types.rs",
            remediation: "define local test-case structs in a sibling test_types.rs",
        }));
    }
    for item in &syntax.items {
        let syn::Item::Use(item_use) = item else {
            continue;
        };
        let syn::UseTree::Path(root) = &item_use.tree else {
            continue;
        };
        if root.ident == constants::SELF_MODULE || root.ident == constants::SUPER_MODULE {
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RST102",
                path: file.relative_path(),
                line: Some(item_use.use_token.span.start().line),
                message: "test uses a relative import",
                remediation: "import through crate:: or the package name",
            }));
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
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST401",
            path: file.relative_path(),
            line,
            message: "module-level TEST_CASES arrays hide cases from their test",
            remediation: "declare let test_cases = [ ... ]; inside the test function",
        }));
    }
    if seen_function {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST105",
            path: file.relative_path(),
            line,
            message: "constant declared after the first test function",
            remediation: "move constants above the tests so setup is visible first",
        }));
    }
    violations
}

fn check_struct_placement(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for item in &syntax.items {
        if let syn::Item::Struct(item_struct) = item {
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RST203",
                path: file.relative_path(),
                line: Some(item_struct.ident.span().start().line),
                message: format!(
                    "struct {} declared outside test_types.rs",
                    item_struct.ident
                ),
                remediation: "move test-case and fixture structs into the area's test_types.rs",
            }));
        }
    }
    violations
}

fn struct_field_names(item_struct: &syn::ItemStruct) -> Vec<String> {
    item_struct.fields.iter().filter_map(field_name).collect()
}

fn field_name(field: &syn::Field) -> Option<String> {
    field.ident.as_ref().map(|ident| ident.to_string())
}

fn has_test_attribute(item_fn: &syn::ItemFn) -> bool {
    item_fn
        .attrs
        .iter()
        .any(|attribute| attribute.path().is_ident("test"))
}
