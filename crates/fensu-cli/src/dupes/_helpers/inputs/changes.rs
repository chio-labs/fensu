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
const QUOTE: char = '"';
const TAB: char = '\t';
const OCTAL_RADIX: u32 = 8;
const OCTAL_WIDTH: usize = 3;

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
            current = target_path(target);
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

/// Decode git's `+++` name: `/dev/null`, a C-quoted path, or a tab-terminated plain path.
fn target_path(target: &str) -> Option<String> {
    let decoded = match target.strip_prefix(QUOTE) {
        Some(quoted) => unquote_c_style(quoted.as_bytes())?,
        None => target.strip_suffix(TAB).unwrap_or(target).to_owned(),
    };
    if decoded == NULL_PATH {
        return None;
    }
    Some(
        decoded
            .strip_prefix(TARGET_PATH_PREFIX)
            .map_or_else(|| decoded.clone(), str::to_owned),
    )
}

/// Undo git's C-style path quoting, including octal-escaped UTF-8 bytes.
fn unquote_c_style(quoted: &[u8]) -> Option<String> {
    let mut decoded: Vec<u8> = Vec::with_capacity(quoted.len());
    let mut index = 0;
    while let Some(&byte) = quoted.get(index) {
        match byte {
            b'"' => return Some(String::from_utf8_lossy(&decoded).into_owned()),
            b'\\' => {
                let (value, width) = unescape(quoted.get(index + 1..)?)?;
                decoded.push(value);
                index += 1 + width;
            }
            other => {
                decoded.push(other);
                index += 1;
            }
        }
    }
    None
}

/// Decode one escape body, returning the byte and how many input bytes it used.
fn unescape(escape: &[u8]) -> Option<(u8, usize)> {
    let first = *escape.first()?;
    let simple = match first {
        b'a' => 0x07,
        b'b' => 0x08,
        b'f' => 0x0c,
        b'n' => b'\n',
        b'r' => b'\r',
        b't' => b'\t',
        b'v' => 0x0b,
        b'0'..=b'7' => {
            let digits = std::str::from_utf8(escape.get(..OCTAL_WIDTH)?).unwrap_or_default();
            return match u8::from_str_radix(digits, OCTAL_RADIX) {
                Ok(value) => Some((value, OCTAL_WIDTH)),
                Err(_) => None,
            };
        }
        other => other,
    };
    Some((simple, 1))
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
