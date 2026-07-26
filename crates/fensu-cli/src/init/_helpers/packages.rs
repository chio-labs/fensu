//! Detect implicit namespace packages and report them.

use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

use walkdir::WalkDir;

const MAX_REPORTED_DIRECTORIES: usize = 10;
const SKIPPED_DIRECTORIES: [&str; 7] = [
    ".git",
    ".venv",
    "venv",
    "target",
    "dist",
    "build",
    "__pycache__",
];

pub(crate) fn implicit_namespace_packages(repository: &Path, roots: &[String]) -> Vec<String> {
    let mut found = BTreeSet::new();
    for root in roots {
        for entry in WalkDir::new(repository.join(root))
            .into_iter()
            .filter_entry(is_walkable)
            .filter_map(Result::ok)
        {
            let path = entry.path();
            if !entry.file_type().is_dir() || path.join("__init__.py").is_file() {
                continue;
            }
            if !holds_python_code(path) {
                continue;
            }
            if let Ok(relative) = path.strip_prefix(repository) {
                found.insert(relative.to_string_lossy().replace('\\', "/"));
            }
        }
    }
    found.into_iter().collect()
}

pub(crate) fn report(directories: &[String]) -> String {
    if directories.is_empty() {
        return String::new();
    }
    let count = directories.len();
    let noun = if count == 1 {
        "directory holds"
    } else {
        "directories hold"
    };
    let mut text = format!("\n-> Implicit namespace packages\n\n    {count} {noun} Python code but no __init__.py:\n\n");
    for directory in directories.iter().take(MAX_REPORTED_DIRECTORIES) {
        text.push_str(&format!("      {directory}\n"));
    }
    if let Some(remaining) = count
        .checked_sub(MAX_REPORTED_DIRECTORIES)
        .filter(|value| *value > 0)
    {
        text.push_str(&format!("      ... and {remaining} more\n"));
    }
    text.push_str(
        "\n    Add __init__.py to each one unless the namespace package is deliberate.\n",
    );
    text
}

fn is_walkable(entry: &walkdir::DirEntry) -> bool {
    entry
        .file_name()
        .to_str()
        .is_none_or(|name| !SKIPPED_DIRECTORIES.contains(&name))
}

fn holds_python_code(directory: &Path) -> bool {
    let Ok(entries) = fs::read_dir(directory) else {
        return false;
    };
    let mut children = entries.filter_map(Result::ok);
    children.any(|child| is_python_module(&child) || is_package_directory(&child))
}

fn is_python_module(child: &fs::DirEntry) -> bool {
    child.path().is_file()
        && child.path().extension().and_then(|value| value.to_str()) == Some("py")
        && child.file_name().to_str() != Some("__init__.py")
}

fn is_package_directory(child: &fs::DirEntry) -> bool {
    child.path().is_dir() && child.path().join("__init__.py").is_file()
}
