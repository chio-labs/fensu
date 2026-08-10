use std::fs;
use std::path::Path;

use crate::analyzer::AnalyzerId;
use crate::models::{ScopedSource, SourcePurpose};

pub(crate) fn web_source(root: &Path, target_path: &str) -> ScopedSource {
    let path = root.join(target_path);
    ScopedSource {
        analyzer: AnalyzerId::TypeScript,
        target_identity: "web".to_owned(),
        parser_contract: AnalyzerId::TypeScript.parser_contract(),
        path: path.clone(),
        repository_path: target_path.to_owned(),
        target_path: target_path.to_owned(),
        test_owner_path: None,
        root: root.join("src"),
        root_text: "src".to_owned(),
        scope: "root".to_owned(),
        relative_parts: target_path.split('/').skip(1).map(str::to_owned).collect(),
        fingerprint: "source-fingerprint".to_owned(),
        content: fs::read(&path).expect("web source content"),
        purpose: SourcePurpose::Direct,
        imports: Vec::new(),
        program: None,
    }
}

#[cfg(windows)]
pub(crate) fn case_sensitive_windows_siblings_remain_confined() -> Option<bool> {
    use std::os::windows::fs::symlink_dir;
    use std::process::Command;

    let repository = tempfile::tempdir().expect("temporary case-sensitive repository");
    let status = Command::new("fsutil")
        .args(["file", "setCaseSensitiveInfo"])
        .arg(repository.path())
        .arg("enable")
        .status()
        .ok()?;
    status.success().then_some(())?;
    let upper = repository.path().join("Repo");
    let lower = repository.path().join("repo");
    fs::create_dir(&upper).expect("upper-case repository");
    fs::create_dir(&lower).expect("lower-case sibling");
    let canonical_upper = dunce::canonicalize(&upper).expect("upper repository canonicalizes");
    let canonical_lower = dunce::canonicalize(&lower).expect("lower sibling canonicalizes");
    let names_are_distinct = crate::repository_io::main::relative_path::relative_path(
        &canonical_lower,
        &canonical_upper,
    )
    .is_none();
    symlink_dir(&lower, upper.join("sibling-link")).ok()?;
    let sibling_is_rejected = crate::configuration::main::resolve_target_root::resolve_target_root(
        &upper,
        "sibling-link",
    )
    .is_err_and(|error| error.contains("must not escape the repository"));
    Some(names_are_distinct && sibling_is_rejected)
}

#[cfg(not(windows))]
pub(crate) fn case_sensitive_windows_siblings_remain_confined() -> Option<bool> {
    None
}
