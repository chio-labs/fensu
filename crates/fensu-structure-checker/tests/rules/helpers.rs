//! Shared temporary-repository helpers for structure checker tests.

use std::collections::BTreeSet;
use std::fs;
use std::path;
use std::sync::atomic;

use crate::test_types;

static REPO_COUNTER: atomic::AtomicUsize = atomic::AtomicUsize::new(0);

/// Write a fixture repository, completing each leaf domain with a `main/` entry.
pub(crate) fn write_temp_repo(test_case: &test_types::CheckRepoTestCase) -> path::PathBuf {
    let root = write_repo(test_case);
    write_missing_entries(&root, test_case);
    root
}

/// Write a fixture whose member is the structure-checker tooling crate.
pub(crate) fn write_tooling_temp_repo(test_case: &test_types::CheckRepoTestCase) -> path::PathBuf {
    let root = write_repo(test_case);
    fs::write(
        root.join("Cargo.toml"),
        "[workspace]\nmembers = [\"crates/fensu-structure-checker\"]\nresolver = \"2\"\n\n[workspace.package]\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[workspace.dependencies]\nfensu-structure-checker = { path = \"crates/fensu-structure-checker\" }\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n",
    )
    .expect("temporary tooling workspace manifest is writable");
    let crate_root = root.join("crates/fensu-structure-checker");
    fs::create_dir_all(&crate_root).expect("temporary tooling crate is writable");
    fs::write(
        crate_root.join("Cargo.toml"),
        "[package]\nname = \"fensu-structure-checker\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n",
    )
    .expect("temporary tooling crate manifest is writable");
    root
}

/// Write a fixture repository exactly as declared, for domain-shape rules.
pub(crate) fn write_temp_repo_verbatim(test_case: &test_types::CheckRepoTestCase) -> path::PathBuf {
    write_repo(test_case)
}

fn write_repo(test_case: &test_types::CheckRepoTestCase) -> path::PathBuf {
    let index = REPO_COUNTER.fetch_add(1, atomic::Ordering::SeqCst);
    let root = std::env::temp_dir().join(format!(
        "fensu-structure-checker-{}-{index}",
        std::process::id()
    ));
    fs::create_dir_all(&root).expect("temporary repository root is writable");
    fs::write(
        root.join("Cargo.toml"),
        "[workspace]\nmembers = [\"crates/example\"]\nresolver = \"2\"\n\n[workspace.package]\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[workspace.dependencies]\nfensu-structure-checker = { path = \"crates/fensu-structure-checker\" }\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n",
    )
    .expect("temporary workspace manifest is writable");
    fs::create_dir_all(root.join("crates/example")).expect("temporary fixture crate is writable");
    fs::write(
        root.join("crates/example/Cargo.toml"),
        "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n",
    )
    .expect("temporary crate manifest is writable");
    for file in &test_case.repo_files {
        let file_path = root.join(&file.path);
        let parent = file_path.parent().expect("fixture paths name a parent");
        fs::create_dir_all(parent).expect("fixture directories are writable");
        fs::write(&file_path, &file.contents).expect("fixture files are writable");
    }
    root
}

fn write_missing_entries(root: &path::Path, test_case: &test_types::CheckRepoTestCase) {
    let domain_parts: Vec<Vec<&str>> = test_case
        .repo_files
        .iter()
        .filter_map(|file| file.path.split_once("/src/"))
        .map(|(_, inside)| inside.split('/').collect::<Vec<&str>>())
        .filter(|parts| parts.len() > 1)
        .collect();
    let domains: BTreeSet<&str> = domain_parts
        .iter()
        .filter_map(|parts| parts.first().copied())
        .collect();
    let entry_domains: BTreeSet<&str> = domain_parts
        .iter()
        .filter(|parts| parts[1] == "main")
        .filter_map(|parts| parts.first().copied())
        .collect();
    let branch_domains: BTreeSet<&str> = domain_parts
        .iter()
        .filter(|parts| parts.len() > 2 && parts[1] != "main" && parts[1] != "_helpers")
        .filter_map(|parts| parts.first().copied())
        .collect();
    let leaf_domains: BTreeSet<&str> = domains.difference(&branch_domains).copied().collect();
    for domain in leaf_domains.difference(&entry_domains) {
        let entry = root.join(format!("crates/example/src/{domain}/main/read_entry.rs"));
        let parent = entry.parent().expect("entry paths name a parent");
        fs::create_dir_all(parent).expect("fixture entry directories are writable");
        fs::write(&entry, "pub fn read_entry() -> usize {\n    1\n}\n")
            .expect("fixture entry files are writable");
    }
}

pub(crate) fn collect_violation_codes(repo_root: &path::Path) -> Vec<&'static str> {
    fensu_structure_checker::rules::main::check_repository::check_repository(repo_root)
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
            path: format!("{directory}/m{index:02}.rs"),
            contents: contents.to_owned(),
        });
    }
    files
}

pub(crate) fn main_module(domain: &str, contents: &str) -> test_types::RepoFile {
    test_types::RepoFile {
        path: format!("crates/example/src/{domain}/main/mod.rs"),
        contents: contents.to_owned(),
    }
}

pub(crate) fn tooling_entry(domain: &str, module: &str) -> test_types::RepoFile {
    test_types::RepoFile {
        path: format!("crates/fensu-structure-checker/src/{domain}/main/{module}.rs"),
        contents: format!("pub(super) fn {module}() -> usize {{\n    1\n}}\n"),
    }
}

pub(crate) fn entry(domain: &str, module: &str, function: &str) -> test_types::RepoFile {
    test_types::RepoFile {
        path: format!("crates/example/src/{domain}/main/{module}.rs"),
        contents: format!("pub(crate) fn {function}() -> usize {{\n    1\n}}\n"),
    }
}

pub(crate) fn entry_with_import(domain: &str, module: &str, import: &str) -> test_types::RepoFile {
    test_types::RepoFile {
        path: format!("crates/example/src/{domain}/main/{module}.rs"),
        contents: format!(
            "{import}\n\npub(crate) fn {module}() -> usize {{\n    read_value()\n}}\n"
        ),
    }
}

pub(crate) fn remove_temp_repo(repo_root: &path::Path) {
    let _ = fs::remove_dir_all(repo_root);
}
