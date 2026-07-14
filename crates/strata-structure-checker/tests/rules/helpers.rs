//! Shared temporary-repository helpers for structure checker tests.

use std::fs;
use std::path;
use std::sync::atomic;

use crate::test_types;

static REPO_COUNTER: atomic::AtomicUsize = atomic::AtomicUsize::new(0);

pub(crate) fn write_temp_repo(test_case: &test_types::CheckRepoTestCase) -> path::PathBuf {
    let index = REPO_COUNTER.fetch_add(1, atomic::Ordering::SeqCst);
    let root = std::env::temp_dir().join(format!(
        "strata-structure-checker-{}-{index}",
        std::process::id()
    ));
    fs::create_dir_all(&root).expect("temporary repository root is writable");
    for file in &test_case.repo_files {
        let file_path = root.join(&file.path);
        let parent = file_path.parent().expect("fixture paths name a parent");
        fs::create_dir_all(parent).expect("fixture directories are writable");
        fs::write(&file_path, &file.contents).expect("fixture files are writable");
    }
    root
}

pub(crate) fn collect_violation_codes(repo_root: &path::Path) -> Vec<&'static str> {
    strata_structure_checker::rules::main::check_repository::check_repository(repo_root)
        .iter()
        .map(|violation| violation.code)
        .collect()
}

pub(crate) fn numbered_module_files(
    directory: &str,
    count: usize,
    contents: &str,
) -> Vec<test_types::RepoFile> {
    let mut files: Vec<test_types::RepoFile> = Vec::new();
    for index in 0..count {
        files.push(test_types::RepoFile {
            path: format!("{directory}/module_{index:02}.rs"),
            contents: contents.to_owned(),
        });
    }
    files
}

pub(crate) fn remove_temp_repo(repo_root: &path::Path) {
    let _ = fs::remove_dir_all(repo_root);
}
