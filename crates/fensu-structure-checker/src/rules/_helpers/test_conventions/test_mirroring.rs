//! Workspace-level test mirroring and harness coverage rules.

use crate::constants;
use crate::models;

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
    violations.extend(runtime_package_violations(
        repo_root,
        &tests_root,
        &src_root,
    ));
    violations.extend(binary_mirror_violations(repo_root, &tests_root, &src_root));
    let entries = match std::fs::read_dir(&tests_root) {
        Ok(entries) => entries,
        Err(error) => {
            let relative = tests_root.strip_prefix(repo_root).unwrap_or(&tests_root);
            return vec![models::Violation::new(models::ViolationRequest {
                code: "RSH901",
                path: relative,
                line: None,
                message: format!("cannot read Rust test directory: {error}"),
                remediation: "restore a readable test directory before checking structure",
            })];
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
            Err(error) => violations.push(models::Violation::new(models::ViolationRequest {
                code: "RSH901",
                path: tests_root.strip_prefix(repo_root).unwrap_or(&tests_root),
                line: None,
                message: format!("cannot inspect Rust test directory entry: {error}"),
                remediation: "restore a readable test directory before checking structure",
            })),
        }
    }
    area_names.sort();
    for name in &area_names {
        if name == constants::BIN_DIRECTORY {
            continue;
        }
        let mirrors_directory = src_root.join(name).is_dir();
        let mirrors_module = src_root.join(format!("{name}.rs")).is_file();
        if mirrors_directory || mirrors_module {
            continue;
        }
        let area = tests_root.join(name);
        let relative = area.strip_prefix(repo_root).unwrap_or(&area);
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST003",
            path: relative,
            line: None,
            message: format!("test area {name} mirrors no source area"),
            remediation: "name test areas after the src module or domain they exercise",
        }));
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST006",
            path: relative,
            line: None,
            message: format!("test area {name} mirrors no source package area"),
            remediation: "create the source area or move the test beneath its owning source area",
        }));
    }
    violations
}

fn runtime_package_violations(
    repo_root: &std::path::Path,
    tests_root: &std::path::Path,
    src_root: &std::path::Path,
) -> Vec<models::Violation> {
    if src_root.join(constants::LIB_FILE).is_file() || !holds_runtime_test_area(tests_root) {
        return Vec::new();
    }
    let relative = tests_root.strip_prefix(repo_root).unwrap_or(tests_root);
    vec![models::Violation::new(models::ViolationRequest {
        code: "RST005",
        path: relative,
        line: None,
        message: "runtime tests mirror a crate with no library package anchor",
        remediation: "add src/lib.rs or move binary tests under tests/bin/<binary>/",
    })]
}

fn holds_runtime_test_area(tests_root: &std::path::Path) -> bool {
    let Ok(entries) = std::fs::read_dir(tests_root) else {
        return false;
    };
    entries.filter_map(Result::ok).any(|entry| {
        entry.path().is_dir() && entry.file_name().to_string_lossy() != constants::BIN_DIRECTORY
    })
}

fn binary_mirror_violations(
    repo_root: &std::path::Path,
    tests_root: &std::path::Path,
    src_root: &std::path::Path,
) -> Vec<models::Violation> {
    let binary_tests = tests_root.join(constants::BIN_DIRECTORY);
    let Ok(entries) = std::fs::read_dir(&binary_tests) else {
        return Vec::new();
    };
    let mut violations: Vec<models::Violation> = Vec::new();
    for result in entries {
        let Ok(entry) = result else {
            continue;
        };
        let path = entry.path();
        if path.is_file() {
            let reserved = path
                .file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| {
                    matches!(name, constants::TEST_TYPES_FILE | constants::HELPERS_FILE)
                });
            if reserved {
                continue;
            }
            let relative = path.strip_prefix(repo_root).unwrap_or(&path);
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RST007",
                path: relative,
                line: None,
                message: "binary test is not nested beneath a binary area",
                remediation: "move the test under tests/bin/<binary>/",
            }));
            continue;
        }
        if !path.is_dir() {
            continue;
        }
        let binary = entry.file_name();
        let flat = src_root
            .join(constants::BIN_DIRECTORY)
            .join(&binary)
            .with_extension(constants::RUST_SUFFIX);
        let nested = src_root
            .join(constants::BIN_DIRECTORY)
            .join(&binary)
            .join(constants::MAIN_FILE);
        if flat.is_file() || nested.is_file() {
            continue;
        }
        let relative = path.strip_prefix(repo_root).unwrap_or(&path);
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST008",
            path: relative,
            line: None,
            message: "binary test area mirrors no Cargo binary",
            remediation: "name the area after a source under src/bin/",
        }));
    }
    violations
}

/// Check that every test module inside a harness area is declared somewhere.
pub(crate) fn check_harness_coverage(
    repo_root: &std::path::Path,
    crate_dir: &std::path::Path,
) -> Vec<models::Violation> {
    let files = test_tree_files(crate_dir);
    let declared = declared_targets(&files);
    let mut violations: Vec<models::Violation> = Vec::new();
    for candidate in area_candidates(&files) {
        if declared.contains(&candidate) {
            continue;
        }
        let relative = candidate.strip_prefix(repo_root).unwrap_or(&candidate);
        let name = candidate
            .file_name()
            .and_then(|value| value.to_str())
            .unwrap_or_default();
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST110",
            path: relative,
            line: None,
            message: format!("test module {name} is never declared and cannot run"),
            remediation:
                "declare #[path = \"<file>.rs\"] mod <file>; from the harness or an area module",
        }));
    }
    violations
}

fn test_tree_files(crate_dir: &std::path::Path) -> Vec<std::path::PathBuf> {
    let mut files: Vec<std::path::PathBuf> = Vec::new();
    for root in [
        crate_dir.join(constants::SOURCE_DIRECTORY),
        crate_dir.join(constants::TESTS_DIRECTORY),
    ] {
        for entry in walkdir::WalkDir::new(&root)
            .follow_links(false)
            .into_iter()
            .filter_map(Result::ok)
        {
            let path = entry.path();
            if entry.file_type().is_file()
                && path.extension().and_then(|value| value.to_str()) == Some("rs")
            {
                files.push(path.to_path_buf());
            }
        }
    }
    files.sort();
    files
}

fn declared_targets(files: &[std::path::PathBuf]) -> std::collections::HashSet<std::path::PathBuf> {
    let mut declared: std::collections::HashSet<std::path::PathBuf> =
        std::collections::HashSet::new();
    for file in files {
        let Some(directory) = file.parent() else {
            continue;
        };
        let area = file.with_extension("");
        let Ok(source) = std::fs::read_to_string(file) else {
            continue;
        };
        let Ok(syntax) = syn::parse_file(&source) else {
            continue;
        };
        for item in &syntax.items {
            let syn::Item::Mod(item_mod) = item else {
                continue;
            };
            let explicit = module_path_attribute(item_mod);
            match explicit {
                Some(value) => {
                    let _ = declared.insert(directory.join(value));
                }
                None => {
                    let name = item_mod.ident.to_string();
                    for base in [directory, area.as_path()] {
                        let _ = declared.insert(base.join(format!("{name}.rs")));
                        let _ = declared.insert(base.join(&name).join(constants::MOD_FILE));
                    }
                }
            }
        }
    }
    declared
}

fn module_path_attribute(item_mod: &syn::ItemMod) -> Option<String> {
    for attribute in &item_mod.attrs {
        if !attribute.path().is_ident("path") {
            continue;
        }
        let syn::Meta::NameValue(value) = &attribute.meta else {
            continue;
        };
        let syn::Expr::Lit(literal) = &value.value else {
            continue;
        };
        if let syn::Lit::Str(text) = &literal.lit {
            return Some(text.value());
        }
    }
    None
}

fn area_candidates(files: &[std::path::PathBuf]) -> Vec<std::path::PathBuf> {
    let mut candidates: Vec<std::path::PathBuf> = Vec::new();
    for file in files {
        let Some(directory) = file.parent() else {
            continue;
        };
        if !directory.with_extension("rs").is_file() {
            continue;
        }
        let inside_tests = directory.file_name().and_then(|value| value.to_str())
            == Some(constants::TESTS_DIRECTORY)
            || directory.ancestors().any(|path| {
                path.file_name().and_then(|value| value.to_str())
                    == Some(constants::TESTS_DIRECTORY)
            });
        if inside_tests {
            candidates.push(file.clone());
        }
    }
    candidates
}
