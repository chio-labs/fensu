//! Lines added or changed since a git revision, including uncommitted and untracked files.

use std::collections::HashMap;
use std::path::Path;
use std::process::Command;

use crate::dupes::models::{CloneUnit, FileChanges};

const TARGET_PREFIX: &str = "+++ ";
const TARGET_PATH_PREFIX: &str = "b/";
const NULL_PATH: &str = "/dev/null";
const HUNK_PREFIX: &str = "@@ -";
const SINGLE_LINE_COUNT: &str = "1";

/// Map repository paths to the worktree lines changed since `revision`.
pub(crate) fn collect_changes_since(
    root: &Path,
    revision: &str,
) -> Result<HashMap<String, FileChanges>, String> {
    let verified = format!("{revision}^{{commit}}");
    let _ = run_git(root, &["rev-parse", "--verify", "--quiet", &verified])
        .map_err(|_| format!("--since revision {revision} is not a commit in this repository."))?;
    let diff = run_git(
        root,
        &[
            "-c",
            "core.quotePath=false",
            "diff",
            "-U0",
            "--no-color",
            "--no-ext-diff",
            "--find-renames",
            "--relative",
            "--src-prefix=a/",
            "--dst-prefix=b/",
            revision,
            "--",
        ],
    )?;
    let mut changes = parse_unified_diff(&diff);
    let untracked = run_git(root, &["ls-files", "--others", "--exclude-standard", "-z"])?;
    for path in untracked.split('\0').filter(|path| !path.is_empty()) {
        changes.insert(
            path.to_owned(),
            FileChanges {
                whole_file: true,
                ..FileChanges::default()
            },
        );
    }
    Ok(changes)
}

/// Parse `git diff -U0` output into added line ranges and pure-deletion points.
pub(crate) fn parse_unified_diff(diff: &str) -> HashMap<String, FileChanges> {
    let mut changes: HashMap<String, FileChanges> = HashMap::new();
    let mut current: Option<String> = None;
    for line in diff.lines() {
        if let Some(target) = line.strip_prefix(TARGET_PREFIX) {
            current = (target != NULL_PATH).then(|| {
                target
                    .strip_prefix(TARGET_PATH_PREFIX)
                    .unwrap_or(target)
                    .to_owned()
            });
            continue;
        }
        let (Some(path), Some(hunk)) = (&current, line.strip_prefix(HUNK_PREFIX)) else {
            continue;
        };
        let Some((start, count)) = added_range(hunk) else {
            continue;
        };
        let entry = changes.entry(path.clone()).or_default();
        if count == 0 {
            entry.deletion_points.push(start);
        } else {
            entry.added_ranges.push((start, start + count - 1));
        }
    }
    changes
}

/// Report whether any line of the unit was added, changed, or had lines deleted inside it.
pub(crate) fn unit_changed(unit: &CloneUnit, changes: Option<&FileChanges>) -> bool {
    let Some(changes) = changes else {
        return false;
    };
    changes.whole_file
        || changes
            .added_ranges
            .iter()
            .any(|(start, end)| *start <= unit.end_line && unit.start_line <= *end)
        || changes
            .deletion_points
            .iter()
            .any(|point| unit.start_line <= *point && *point < unit.end_line)
}

fn added_range(hunk: &str) -> Option<(usize, usize)> {
    let added = hunk.split_whitespace().nth(1)?.strip_prefix('+')?;
    let (start, count) = added.split_once(',').unwrap_or((added, SINGLE_LINE_COUNT));
    match (start.parse(), count.parse()) {
        (Ok(start), Ok(count)) => Some((start, count)),
        _ => None,
    }
}

fn run_git(root: &Path, arguments: &[&str]) -> Result<String, String> {
    let output = Command::new("git")
        .args(arguments)
        .current_dir(root)
        .output()
        .map_err(|error| format!("Could not run git: {error}"))?;
    if !output.status.success() {
        return Err(format!(
            "git {} failed: {}",
            arguments.join(" "),
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}
