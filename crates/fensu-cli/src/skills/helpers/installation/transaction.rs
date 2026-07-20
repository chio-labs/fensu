use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use crate::skills::helpers::installation::filesystem::{
    capture, create_safe_parents, ensure_snapshot, set_mode, Snapshot,
};

static TEMP_SEQUENCE: AtomicU64 = AtomicU64::new(0);

#[derive(Clone, Debug)]
pub(crate) struct Publication {
    pub(crate) snapshot: Snapshot,
    pub(crate) content: Vec<u8>,
    pub(crate) mode: Option<u32>,
}

#[derive(Debug)]
struct StagedPublication {
    publication: Publication,
    staged: PathBuf,
    backup: Option<PathBuf>,
    published: Option<Snapshot>,
}

#[derive(Debug)]
struct StagedDeletion {
    snapshot: Snapshot,
    backup: PathBuf,
    published: bool,
}

pub(crate) fn publish(
    publications: Vec<Publication>,
    deletions: Vec<Snapshot>,
) -> Result<(), String> {
    for publication in &publications {
        ensure_snapshot(&publication.snapshot)?;
    }
    for deletion in &deletions {
        ensure_snapshot(deletion)?;
    }
    let mut staged = Vec::new();
    let mut staged_deletions = Vec::new();
    let mut created_directories = Vec::new();
    let result = (|| {
        for publication in publications {
            let parent = publication
                .snapshot
                .path
                .parent()
                .ok_or_else(|| "Publication target has no parent.".to_owned())?;
            create_safe_parents(parent, &mut created_directories)?;
            let path = stage_file(
                &publication.snapshot.path,
                &publication.content,
                publication.mode,
            )?;
            staged.push(StagedPublication {
                publication,
                staged: path,
                backup: None,
                published: None,
            });
        }
        for snapshot in deletions {
            let backup = temporary_path(&snapshot.path, "delete")?;
            staged_deletions.push(StagedDeletion {
                snapshot,
                backup,
                published: false,
            });
        }
        for item in &mut staged {
            ensure_snapshot(&item.publication.snapshot)?;
            if item.publication.snapshot.content.is_some() {
                let backup = temporary_path(&item.publication.snapshot.path, "backup")?;
                fs::rename(&item.publication.snapshot.path, &backup)
                    .map_err(|error| format!("failed to install skill files: {error}"))?;
                let moved = capture(&backup)?;
                if !same_snapshot_state(&item.publication.snapshot, &moved) {
                    if !item.publication.snapshot.path.exists() {
                        let _ = fs::rename(&backup, &item.publication.snapshot.path);
                    }
                    return Err(format!(
                        "skill target changed during update: {}",
                        item.publication.snapshot.path.display()
                    ));
                }
                item.backup = Some(backup);
            }
            fs::hard_link(&item.staged, &item.publication.snapshot.path)
                .map_err(|error| format!("failed to install skill files: {error}"))?;
            item.published = Some(capture(&item.publication.snapshot.path)?);
        }
        for deletion in &mut staged_deletions {
            ensure_snapshot(&deletion.snapshot)?;
            fs::rename(&deletion.snapshot.path, &deletion.backup)
                .map_err(|error| format!("failed to install skill files: {error}"))?;
            let moved = capture(&deletion.backup)?;
            if !same_snapshot_state(&deletion.snapshot, &moved) {
                if !deletion.snapshot.path.exists() {
                    let _ = fs::rename(&deletion.backup, &deletion.snapshot.path);
                }
                return Err(format!(
                    "legacy skill target changed during migration: {}",
                    deletion.snapshot.path.display()
                ));
            }
            deletion.published = true;
        }
        Ok(())
    })();
    if let Err(error) = result {
        rollback(&mut staged, &mut staged_deletions);
        for directory in created_directories.into_iter().rev() {
            let _ = fs::remove_dir(directory);
        }
        return Err(error);
    }
    for item in &staged {
        let _ = fs::remove_file(&item.staged);
        if let Some(backup) = &item.backup {
            let _ = fs::remove_file(backup);
        }
    }
    for item in &staged_deletions {
        let _ = fs::remove_file(&item.backup);
    }
    Ok(())
}

fn rollback(publications: &mut [StagedPublication], deletions: &mut [StagedDeletion]) {
    for deletion in deletions.iter_mut().rev() {
        if deletion.published && !deletion.snapshot.path.exists() {
            let _ = fs::rename(&deletion.backup, &deletion.snapshot.path);
        }
    }
    for item in publications.iter_mut().rev() {
        if let Some(published) = &item.published {
            if capture(&published.path).is_ok_and(|current| current == *published) {
                let _ = fs::remove_file(&published.path);
            }
        }
        if let Some(backup) = &item.backup {
            if !item.publication.snapshot.path.exists() {
                let _ = fs::rename(backup, &item.publication.snapshot.path);
            } else {
                let _ = fs::remove_file(backup);
            }
        }
        let _ = fs::remove_file(&item.staged);
    }
}

fn same_snapshot_state(left: &Snapshot, right: &Snapshot) -> bool {
    left.content == right.content && left.mode == right.mode && left.identity == right.identity
}

fn stage_file(destination: &Path, content: &[u8], mode: Option<u32>) -> Result<PathBuf, String> {
    let path = temporary_path(destination, "stage")?;
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&path)
        .map_err(|error| format!("failed to install skill files: {error}"))?;
    file.write_all(content)
        .map_err(|error| format!("failed to install skill files: {error}"))?;
    file.sync_all()
        .map_err(|error| format!("failed to install skill files: {error}"))?;
    set_mode(&path, mode)?;
    Ok(path)
}

fn temporary_path(destination: &Path, purpose: &str) -> Result<PathBuf, String> {
    let parent = destination
        .parent()
        .ok_or_else(|| "Skill target has no parent.".to_owned())?;
    for _ in 0..1000 {
        let sequence = TEMP_SEQUENCE.fetch_add(1, Ordering::Relaxed);
        let path = parent.join(format!(
            ".fensu-{purpose}-{}-{sequence}",
            std::process::id()
        ));
        if !path.exists() {
            return Ok(path);
        }
    }
    Err("Could not allocate a skill transaction staging path.".to_owned())
}
