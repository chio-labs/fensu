//! Shared temporary-repository helpers for structure checker tests.

use std::collections::BTreeSet;
use std::fmt::Write as _;
use std::fs;
use std::path;
use std::sync::atomic;

use crate::test_types;
use fensu_structure_checker::constants;

static REPO_COUNTER: atomic::AtomicUsize = atomic::AtomicUsize::new(0);

/// Write a fixture repository, completing each leaf domain with a `main/` entry.
pub(crate) fn write_temp_repo(test_case: &test_types::CheckRepoTestCase) -> path::PathBuf {
    let root = write_repo(test_case);
    write_default_library_root(&root, test_case);
    write_missing_test_types(&root, test_case);
    write_missing_integration_harnesses(&root);
    write_missing_entries(&root, test_case);
    root
}

fn write_default_library_root(root: &path::Path, test_case: &test_types::CheckRepoTestCase) {
    let has_test_topic = test_case
        .repo_files
        .iter()
        .any(|file| is_test_topic(&file.path));
    let library = root.join("crates/example/src/lib.rs");
    let _ = (has_test_topic && !library.is_file()).then(|| {
        fs::create_dir_all(library.parent().expect("library root has a parent"))
            .expect("fixture source directory is writable");
        fs::write(&library, "#![forbid(unsafe_code)]\n").expect("fixture library root is writable");
    });
}

fn write_missing_test_types(root: &path::Path, test_case: &test_types::CheckRepoTestCase) {
    let paths = test_case
        .repo_files
        .iter()
        .filter(|file| {
            is_test_topic(&file.path)
                && !matches!(
                    file.path.rsplit('/').next(),
                    Some("helpers.rs" | "test_types.rs")
                )
        })
        .map(|file| {
            root.join(&file.path)
                .with_file_name(constants::TEST_TYPES_FILE)
        })
        .filter(|path| !path.is_file())
        .collect::<Vec<_>>();
    for path in paths {
        fs::write(
            path,
            "pub(crate) struct ValueTestCase {\n    pub(crate) description: &'static str,\n    pub(crate) expected_value: usize,\n}\n",
        )
        .expect("fixture test types are writable");
    }
}

fn is_test_topic(path: &str) -> bool {
    path.split_once("/tests/")
        .is_some_and(|(_, inside)| inside.contains('/'))
}

/// Write a fixture whose member is the structure-checker tooling crate.
pub(crate) fn write_tooling_temp_repo(test_case: &test_types::CheckRepoTestCase) -> path::PathBuf {
    let root = write_repo(test_case);
    fs::write(
        root.join("Cargo.toml"),
        "[workspace]\nmembers = [\"crates/fensu-structure-checker\"]\nresolver = \"2\"\n\n[workspace.package]\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[workspace.dependencies]\nfensu-structure-checker = \"0.12.0\"\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n",
    )
    .expect("temporary tooling workspace manifest is writable");
    let crate_root = root.join("crates/fensu-structure-checker");
    fs::create_dir_all(&crate_root).expect("temporary tooling crate is writable");
    fs::write(
        crate_root.join("Cargo.toml"),
        "[package]\nname = \"fensu-structure-checker\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n",
    )
    .expect("temporary tooling crate manifest is writable");
    fs::create_dir_all(crate_root.join("src")).expect("temporary tooling source is writable");
    fs::write(crate_root.join("src/lib.rs"), "#![forbid(unsafe_code)]\n")
        .expect("temporary tooling library root is writable");
    root
}

/// Write a fixture repository exactly as declared, for domain-shape rules.
pub(crate) fn write_temp_repo_verbatim(test_case: &test_types::CheckRepoTestCase) -> path::PathBuf {
    let root = write_repo(test_case);
    write_missing_integration_harnesses(&root);
    root
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
        "[workspace]\nmembers = [\"crates/example\"]\nresolver = \"2\"\n\n[workspace.package]\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[workspace.dependencies]\nfensu-structure-checker = \"0.12.0\"\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n",
    )
    .expect("temporary workspace manifest is writable");
    fs::create_dir_all(root.join("crates/example")).expect("temporary fixture crate is writable");
    fs::write(
        root.join("crates/example/Cargo.toml"),
        "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n",
    )
    .expect("temporary crate manifest is writable");
    fs::create_dir_all(root.join("crates/example/src"))
        .expect("temporary fixture source directory is writable");
    fs::write(
        root.join("crates/example/src/lib.rs"),
        "#![forbid(unsafe_code)]\n",
    )
    .expect("temporary fixture library root is writable");
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

fn write_missing_integration_harnesses(root: &path::Path) {
    let tests_root = root.join("crates/example/tests");
    let Ok(entries) = fs::read_dir(&tests_root) else {
        return;
    };
    for entry in entries.filter_map(Result::ok).filter(|entry| {
        entry.path().is_dir()
            && !tests_root
                .join(format!("{}.rs", entry.file_name().to_string_lossy()))
                .exists()
    }) {
        let area = entry.file_name().to_string_lossy().into_owned();
        let harness = tests_root.join(format!("{area}.rs"));
        let mut modules = walkdir::WalkDir::new(entry.path())
            .min_depth(1)
            .max_depth(1)
            .into_iter()
            .filter_map(Result::ok)
            .filter(|candidate| {
                candidate.file_type().is_file()
                    && candidate
                        .path()
                        .extension()
                        .and_then(|value| value.to_str())
                        == Some("rs")
            })
            .map(|candidate| candidate.file_name().to_string_lossy().into_owned())
            .collect::<Vec<_>>();
        modules.sort();
        let mut source = String::new();
        for (index, file) in modules.iter().enumerate() {
            writeln!(source, "#[path = \"{area}/{file}\"]\nmod fixture_{index};")
                .expect("writing to a string succeeds");
        }
        fs::write(harness, source).expect("temporary integration harness is writable");
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
