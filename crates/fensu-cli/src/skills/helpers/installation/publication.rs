use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

use crate::skills::helpers::content::fingerprint::{
    generated_marker_present, owned_project_content, parse_ownership, project_marker_present,
};
use crate::skills::helpers::installation::filesystem::{
    capture, capture_bundle, ensure_safe_directory, normalization_collision, sorted_entries,
    Snapshot,
};
use crate::skills::helpers::installation::plan::skills_directory;
use crate::skills::helpers::installation::transaction::{self, Publication};
use crate::skills::models::InstallPlan;

pub(crate) fn install(
    plan: &InstallPlan,
    generated: &[u8],
    force: bool,
) -> Result<Vec<PathBuf>, String> {
    let mut publications = Vec::new();
    let mut deletions = HashMap::<PathBuf, Snapshot>::new();
    let mut stale_roots = Vec::new();
    let mut written = Vec::new();
    for target in &plan.targets {
        let root = target
            .path
            .parent()
            .ok_or_else(|| "Skill target has no parent.".to_owned())?;
        let existing = preflight_bundle(root, &plan.owner, &plan.context.identity, false, force)?;
        let by_path = existing
            .iter()
            .map(|item| (item.path.clone(), item.clone()))
            .collect::<HashMap<_, _>>();
        let snapshot = by_path
            .get(&target.path)
            .cloned()
            .unwrap_or(capture(&target.path)?);
        publications.push(Publication {
            mode: snapshot.mode.or(Some(0o644)),
            snapshot,
            content: generated.to_vec(),
        });
        written.push(target.path.clone());
        for snapshot in existing {
            if snapshot.path != target.path {
                deletions.insert(snapshot.path.clone(), snapshot);
            }
        }
    }
    for target in &plan.project_targets {
        let existing = preflight_bundle(
            &target.path,
            &plan.owner,
            &target.bundle.identity,
            true,
            force,
        )?;
        let by_path = existing
            .iter()
            .map(|item| (item.path.clone(), item.clone()))
            .collect::<HashMap<_, _>>();
        let document = owned_project_content(&plan.context, &target.bundle)?;
        let mut desired = HashSet::new();
        for source in &target.bundle.files {
            let path = target.path.join(&source.relative_path);
            desired.insert(path.clone());
            let snapshot = by_path.get(&path).cloned().unwrap_or(capture(&path)?);
            let content = if source.relative_path == Path::new("SKILL.md") {
                document.clone()
            } else {
                source.content.clone()
            };
            publications.push(Publication {
                snapshot,
                content,
                mode: Some(source.mode),
            });
            written.push(path);
        }
        for snapshot in existing {
            if !desired.contains(&snapshot.path) {
                deletions.insert(snapshot.path.clone(), snapshot);
            }
        }
    }
    if plan.synchronize_project_skills {
        stale_roots = capture_stale_bundles(plan, &mut deletions)?;
    }
    for path in &plan.legacy_paths {
        if let Some(snapshot) = capture_legacy(path, &plan.owner)? {
            deletions.insert(path.clone(), snapshot);
        }
    }
    transaction::publish(publications, deletions.into_values().collect())?;
    cleanup_empty_roots(plan, stale_roots);
    Ok(written)
}

fn preflight_bundle(
    root: &Path,
    expected_owner: &str,
    identity: &str,
    project: bool,
    force: bool,
) -> Result<Vec<Snapshot>, String> {
    if let Some(collision) = normalization_collision(&root.join("SKILL.md"))? {
        return Err(format!(
            "skill identity normalization collides: {} and {}",
            root.display(),
            collision.display()
        ));
    }
    let existing = capture_bundle(root)?;
    if existing.is_empty() {
        return Ok(existing);
    }
    let document = existing
        .iter()
        .find(|item| item.path == root.join("SKILL.md"));
    let ownership = document
        .and_then(|item| item.content.as_deref())
        .and_then(parse_ownership);
    if ownership
        .as_ref()
        .is_some_and(|item| item.owner != expected_owner || item.identity != identity)
    {
        return Err(format!(
            "refusing to overwrite skill owned by another Fensu project: {}",
            root.join("SKILL.md").display()
        ));
    }
    let content = document.and_then(|item| item.content.as_deref());
    let managed = ownership
        .as_ref()
        .is_some_and(|item| item.owner == expected_owner)
        && content.is_some_and(|bytes| {
            if project {
                project_marker_present(bytes)
            } else {
                generated_marker_present(bytes)
            }
        });
    let compatible =
        !project && ownership.is_none() && content.is_some_and(generated_marker_present);
    if !managed && !compatible && !force {
        return Err(format!(
            "refusing to overwrite unmanaged skill file: {}; rerun with --force",
            root.join("SKILL.md").display()
        ));
    }
    Ok(existing)
}

fn capture_stale_bundles(
    plan: &InstallPlan,
    deletions: &mut HashMap<PathBuf, Snapshot>,
) -> Result<Vec<PathBuf>, String> {
    let mut stale_roots = Vec::new();
    let desired = plan
        .project_targets
        .iter()
        .map(|target| target.bundle.identity.to_ascii_lowercase())
        .chain(std::iter::once(plan.context.identity.to_ascii_lowercase()))
        .collect::<HashSet<_>>();
    let directories = plan
        .targets
        .iter()
        .map(|target| skills_directory(&target.path))
        .collect::<Result<HashSet<_>, _>>()?;
    for directory in directories {
        if !directory.exists() {
            continue;
        }
        ensure_safe_directory(&directory)?;
        for entry in sorted_entries(&directory)? {
            let name = entry
                .file_name()
                .and_then(|value| value.to_str())
                .unwrap_or_default();
            if desired.contains(&name.to_ascii_lowercase()) || !entry.is_dir() {
                continue;
            }
            let document = capture(&entry.join("SKILL.md"))?;
            let Some(content) = document.content.as_deref() else {
                continue;
            };
            let Some(ownership) = parse_ownership(content) else {
                continue;
            };
            if project_marker_present(content)
                && ownership.owner == plan.owner
                && ownership.identity == name
            {
                stale_roots.push(entry.clone());
                for snapshot in capture_bundle(&entry)? {
                    deletions.insert(snapshot.path.clone(), snapshot);
                }
            }
        }
    }
    Ok(stale_roots)
}

fn capture_legacy(path: &Path, expected_owner: &str) -> Result<Option<Snapshot>, String> {
    if fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink()) {
        return Err(format!(
            "refusing to write unsafe skill target: {}",
            path.display()
        ));
    }
    let snapshot = capture(path)?;
    let Some(content) = snapshot.content.as_deref() else {
        return Ok(None);
    };
    if !generated_marker_present(content) {
        return Ok(None);
    }
    if let Some(ownership) = parse_ownership(content) {
        if ownership.owner != expected_owner {
            return Ok(None);
        }
    }
    Ok(Some(snapshot))
}

fn cleanup_empty_roots(plan: &InstallPlan, stale_roots: Vec<PathBuf>) {
    let roots = plan
        .project_targets
        .iter()
        .map(|target| target.path.clone())
        .chain(
            plan.legacy_paths
                .iter()
                .filter_map(|path| path.parent().map(Path::to_path_buf)),
        )
        .chain(stale_roots)
        .collect::<HashSet<_>>();
    for root in roots {
        let mut directories = Vec::new();
        if root.is_dir() {
            for entry in walkdir::WalkDir::new(&root)
                .min_depth(1)
                .into_iter()
                .filter_map(Result::ok)
            {
                if entry.file_type().is_dir() {
                    directories.push(entry.path().to_path_buf());
                }
            }
        }
        directories.sort_by_key(|path| std::cmp::Reverse(path.components().count()));
        directories.push(root);
        for directory in directories {
            let _ = fs::remove_dir(directory);
        }
    }
}
