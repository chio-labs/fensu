//! Collect workspace source files and dispatch per-file rule families.

use std::fs;
use std::path;

use crate::constants;
use crate::models;
use crate::rules::helpers::containers;
use crate::rules::helpers::hygiene;
use crate::rules::helpers::layers;
use crate::rules::helpers::naming;
use crate::rules::helpers::role_files;
use crate::rules::helpers::roles;
use crate::rules::helpers::shape;
use crate::rules::helpers::tests_layout;
use crate::rules::helpers::tests_shape;
use crate::types::FileKind;

/// Read the root workspace manifest and return its explicit member crates.
pub(crate) fn scan_workspace(repo_root: &path::Path) -> models::WorkspaceScan {
    let manifest_path = repo_root.join(constants::CARGO_MANIFEST_FILE);
    let source = match fs::read_to_string(&manifest_path) {
        Ok(value) => value,
        Err(error) => {
            return models::WorkspaceScan {
                crate_directories: Vec::new(),
                violations: vec![manifest_setup_violation(
                    repo_root,
                    &manifest_path,
                    format!("cannot read workspace manifest: {error}"),
                )],
            };
        }
    };
    let manifest = match toml::from_str::<toml::Value>(&source) {
        Ok(value) => value,
        Err(error) => {
            return models::WorkspaceScan {
                crate_directories: Vec::new(),
                violations: vec![manifest_setup_violation(
                    repo_root,
                    &manifest_path,
                    format!("cannot parse workspace manifest: {error}"),
                )],
            };
        }
    };
    let mut violations = workspace_lint_violations(repo_root, &manifest_path, &manifest);
    let relative_manifest = manifest_path
        .strip_prefix(repo_root)
        .unwrap_or(&manifest_path);
    violations.extend(layers::workspace_dependency_policy_violations(
        relative_manifest,
        &manifest,
    ));
    let members = manifest
        .get(constants::WORKSPACE_KEY)
        .and_then(|value| value.get(constants::MEMBERS_KEY))
        .and_then(toml::Value::as_array);
    let Some(members) = members else {
        violations.push(manifest_setup_violation(
            repo_root,
            &manifest_path,
            "workspace manifest declares no member list",
        ));
        return models::WorkspaceScan {
            crate_directories: Vec::new(),
            violations,
        };
    };
    let mut crate_directories: Vec<path::PathBuf> = Vec::new();
    for member in members {
        let Some(relative) = member.as_str() else {
            violations.push(manifest_setup_violation(
                repo_root,
                &manifest_path,
                "workspace member is not a path string",
            ));
            continue;
        };
        let member_path = path::Path::new(relative);
        if !valid_member_path(member_path) {
            violations.push(manifest_setup_violation(
                repo_root,
                &manifest_path,
                format!(
                    "workspace member path is not explicit and repository-relative: {relative}"
                ),
            ));
            continue;
        }
        let crate_dir = repo_root.join(member_path);
        if !crate_dir.is_dir() || !crate_dir.join(constants::CARGO_MANIFEST_FILE).is_file() {
            violations.push(manifest_setup_violation(
                repo_root,
                &manifest_path,
                format!("workspace member has no crate manifest: {relative}"),
            ));
            continue;
        }
        crate_directories.push(crate_dir);
    }
    crate_directories.sort();
    crate_directories.dedup();
    models::WorkspaceScan {
        crate_directories,
        violations,
    }
}

pub(crate) fn rust_files(repo_root: &path::Path, root: &path::Path) -> models::SourceScan {
    let mut files: Vec<models::SourceFile> = Vec::new();
    let mut violations: Vec<models::Violation> = Vec::new();
    if !root.exists() {
        return models::SourceScan { files, violations };
    }
    let mut paths: Vec<path::PathBuf> = Vec::new();
    for result in walkdir::WalkDir::new(root) {
        match result {
            Ok(entry) => {
                let extension = entry.path().extension().and_then(|value| value.to_str());
                if entry.path().is_file() && extension == Some(constants::RUST_SUFFIX) {
                    paths.push(entry.path().to_path_buf());
                }
            }
            Err(error) => {
                let failed_path = error.path().unwrap_or(root);
                violations.push(models::Violation::new(
                    "RSH901",
                    path::Path::new(&relative_display(repo_root, failed_path)),
                    None,
                    format!("cannot traverse Rust source tree: {error}"),
                    "restore a readable source tree before checking structure",
                ));
            }
        }
    }
    paths.sort();
    for path in paths {
        match fs::read_to_string(&path) {
            Ok(source) => files.push(models::SourceFile {
                relative: relative_display(repo_root, &path),
                path,
                source,
            }),
            Err(error) => violations.push(models::Violation::new(
                "RSH901",
                path::Path::new(&relative_display(repo_root, &path)),
                None,
                format!("cannot read Rust source: {error}"),
                "restore a readable UTF-8 source file before checking structure",
            )),
        }
    }
    models::SourceScan { files, violations }
}

pub(crate) fn check_source_file(
    repo_root: &path::Path,
    src_root: &path::Path,
    file: &models::SourceFile,
) -> Vec<models::Violation> {
    if let Some(kind) = inline_test_file_kind(file) {
        return check_test_syntax(file, kind);
    }
    let kind = source_file_kind(file, repo_root, src_root);
    let syntax = syn::parse_file(&file.source);
    let mut violations = hygiene::check_source(file, syntax.as_ref().ok(), kind);
    violations.extend(roles::check_common(file));
    match syntax.as_ref() {
        Ok(syntax) => {
            violations.extend(layers::check_uses(file, syntax, true));
            violations.extend(roles::check_source(file, syntax, kind));
            violations.extend(containers::check_file(file, syntax, kind));
            violations.extend(role_files::check(file, syntax, kind));
            violations.extend(naming::check(file, syntax));
            violations.extend(shape::check(file, syntax, kind));
        }
        Err(error) => violations.push(parse_violation(file, error)),
    }
    violations
}

pub(crate) fn check_test_file(
    repo_root: &path::Path,
    tests_root: &path::Path,
    file: &models::SourceFile,
) -> Vec<models::Violation> {
    let kind = test_file_kind(file, repo_root, tests_root);
    check_test_syntax(file, kind)
}

fn check_test_syntax(file: &models::SourceFile, kind: FileKind) -> Vec<models::Violation> {
    let syntax = syn::parse_file(&file.source);
    let mut violations = hygiene::check_test_file(file, syntax.as_ref().ok());
    violations.extend(roles::check_common(file));
    match syntax.as_ref() {
        Ok(syntax) => {
            violations.extend(layers::check_uses(file, syntax, false));
            violations.extend(tests_layout::check(file, syntax, kind));
            violations.extend(tests_shape::check(file, syntax, kind));
        }
        Err(error) => violations.push(parse_violation(file, error)),
    }
    violations
}

fn inline_test_file_kind(file: &models::SourceFile) -> Option<FileKind> {
    if file.file_name() == constants::INLINE_TEST_HARNESS_FILE
        && file.path.with_extension("").is_dir()
    {
        return Some(FileKind::TestHarness);
    }
    let tests_directory = file.path.ancestors().find(|path| {
        path.file_name().and_then(|name| name.to_str()) == Some(constants::TESTS_DIRECTORY)
            && path.with_extension("rs").is_file()
    })?;
    (file.path != tests_directory).then(|| match file.file_name() {
        "test_types.rs" => FileKind::TestTypes,
        "helpers.rs" => FileKind::TestHelpers,
        _ => FileKind::TestTopic,
    })
}

fn parse_violation(file: &models::SourceFile, error: &syn::Error) -> models::Violation {
    models::Violation::new(
        "RSH902",
        file.relative_path(),
        Some(error.span().start().line),
        format!("cannot parse Rust source: {error}"),
        "fix the syntax error before checking structure",
    )
}

pub(crate) fn manifest_setup_violation(
    repo_root: &path::Path,
    manifest_path: &path::Path,
    message: impl Into<String>,
) -> models::Violation {
    let relative = manifest_path
        .strip_prefix(repo_root)
        .unwrap_or(manifest_path);
    models::Violation::new(
        "RSL901",
        relative,
        None,
        message,
        "restore a readable, valid Cargo manifest before checking structure",
    )
}

fn valid_member_path(member: &path::Path) -> bool {
    !member.is_absolute()
        && member.components().all(|component| {
            matches!(
                component,
                path::Component::Normal(_) | path::Component::CurDir
            )
        })
}

fn workspace_lint_violations(
    repo_root: &path::Path,
    manifest_path: &path::Path,
    manifest: &toml::Value,
) -> Vec<models::Violation> {
    let relative = manifest_path
        .strip_prefix(repo_root)
        .unwrap_or(manifest_path);
    let mut violations: Vec<models::Violation> = Vec::new();
    let workspace = manifest.get(constants::WORKSPACE_KEY);
    let lint_root = workspace.and_then(|value| value.get(constants::LINTS_KEY));
    for (name, level) in constants::REQUIRED_RUST_LINTS {
        let actual = lint_root
            .and_then(|value| value.get(constants::RUST_KEY))
            .and_then(|value| value.get(*name))
            .and_then(toml::Value::as_str);
        if actual != Some(*level) {
            violations.push(models::Violation::new(
                "RSL303",
                relative,
                None,
                format!("workspace Rust lint {name} is not set to {level}"),
                "declare the required lint level under [workspace.lints.rust]",
            ));
        }
    }
    for (name, level) in constants::REQUIRED_CLIPPY_LINTS {
        let actual = lint_root
            .and_then(|value| value.get(constants::CLIPPY_KEY))
            .and_then(|value| value.get(*name))
            .and_then(toml::Value::as_str);
        if actual != Some(*level) {
            violations.push(models::Violation::new(
                "RSL303",
                relative,
                None,
                format!("workspace Clippy lint {name} is not set to {level}"),
                "declare the required lint level under [workspace.lints.clippy]",
            ));
        }
    }
    violations
}

pub(crate) fn relative_display(repo_root: &path::Path, path: &path::Path) -> String {
    let relative = path.strip_prefix(repo_root).unwrap_or(path);
    let parts: Vec<String> = relative
        .components()
        .map(|component| component.as_os_str().to_string_lossy().into_owned())
        .collect();
    parts.join("/")
}

fn source_file_kind(
    file: &models::SourceFile,
    repo_root: &path::Path,
    src_root: &path::Path,
) -> FileKind {
    let lib_root = relative_display(repo_root, &src_root.join(constants::LIB_FILE));
    let bin_adapter = relative_display(repo_root, &src_root.join(constants::MAIN_FILE));
    if file.relative == lib_root {
        return FileKind::LibraryRoot;
    }
    if file.relative == bin_adapter {
        return FileKind::BinAdapter;
    }
    if file.file_name() == constants::MOD_FILE {
        return FileKind::ModRoot;
    }
    FileKind::ModuleFile
}

fn test_file_kind(
    file: &models::SourceFile,
    repo_root: &path::Path,
    tests_root: &path::Path,
) -> FileKind {
    let tests_prefix = relative_display(repo_root, tests_root);
    let inside = file
        .relative
        .strip_prefix(&format!("{tests_prefix}/"))
        .unwrap_or(&file.relative);
    if !inside.contains('/') {
        return FileKind::TestHarness;
    }
    match file.file_name() {
        "test_types.rs" => FileKind::TestTypes,
        "helpers.rs" => FileKind::TestHelpers,
        _ => FileKind::TestTopic,
    }
}
