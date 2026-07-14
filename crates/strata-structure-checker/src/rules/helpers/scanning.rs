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

pub(crate) fn crate_directories(repo_root: &path::Path) -> Vec<path::PathBuf> {
    let crates_root = repo_root.join("crates");
    let mut directories: Vec<path::PathBuf> = Vec::new();
    let Ok(entries) = fs::read_dir(&crates_root) else {
        return directories;
    };
    for entry in entries.flatten() {
        if entry.path().is_dir() {
            directories.push(entry.path());
        }
    }
    directories.sort();
    directories
}

pub(crate) fn rust_files(repo_root: &path::Path, root: &path::Path) -> Vec<models::SourceFile> {
    let mut files: Vec<models::SourceFile> = Vec::new();
    if !root.exists() {
        return files;
    }
    let mut paths: Vec<path::PathBuf> = Vec::new();
    for entry in walkdir::WalkDir::new(root).into_iter().flatten() {
        let extension = entry.path().extension().and_then(|value| value.to_str());
        if entry.path().is_file() && extension == Some(constants::RUST_SUFFIX) {
            paths.push(entry.path().to_path_buf());
        }
    }
    paths.sort();
    for path in paths {
        let source = fs::read_to_string(&path).unwrap_or_default();
        files.push(models::SourceFile {
            relative: relative_display(repo_root, &path),
            path,
            source,
        });
    }
    files
}

pub(crate) fn check_source_file(
    repo_root: &path::Path,
    src_root: &path::Path,
    file: &models::SourceFile,
) -> Vec<models::Violation> {
    let kind = source_file_kind(file, repo_root, src_root);
    let syntax = syn::parse_file(&file.source).ok();
    let mut violations = hygiene::check_source(file, syntax.as_ref(), kind);
    violations.extend(roles::check_common(file));
    if let Some(syntax) = syntax.as_ref() {
        violations.extend(layers::check_uses(file, syntax, true));
        violations.extend(roles::check_source(file, syntax, kind));
        violations.extend(containers::check_file(file, syntax, kind));
        violations.extend(role_files::check(file, syntax, kind));
        violations.extend(naming::check(file, syntax));
        violations.extend(shape::check(file, syntax, kind));
    }
    violations
}

pub(crate) fn check_test_file(
    repo_root: &path::Path,
    tests_root: &path::Path,
    file: &models::SourceFile,
) -> Vec<models::Violation> {
    let kind = test_file_kind(file, repo_root, tests_root);
    let syntax = syn::parse_file(&file.source).ok();
    let mut violations = hygiene::check_test_file(file, syntax.as_ref());
    violations.extend(roles::check_common(file));
    if let Some(syntax) = syntax.as_ref() {
        violations.extend(layers::check_uses(file, syntax, false));
        violations.extend(tests_layout::check(file, syntax, kind));
        violations.extend(tests_shape::check(file, syntax, kind));
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
