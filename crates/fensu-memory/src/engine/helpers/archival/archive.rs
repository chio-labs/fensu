//! Deterministic archive planning, rollback-safe moves, and synchronization.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Component, Path, PathBuf};
use std::time::{Duration, SystemTime};

use crate::engine::errors::MemoryIndexError;
use crate::engine::models::{MemoryArchiveMove, MemoryArchiveResult};
use crate::source::main::discover_memory::discover_memory;
use crate::source::models::{DiscoveredDocument, SourceMetadata};
use crate::source::types::{ArchiveState, ArtifactKind, TaskLifecycle};

const SECONDS_PER_DAY: u64 = 86_400;

#[derive(Clone, Debug, Eq, PartialEq)]
struct PlannedMove {
    source_path: PathBuf,
    destination_path: PathBuf,
    source_relative: String,
    destination_relative: String,
}

pub(crate) fn archive(
    repository_root: &Path,
    database_path: &Path,
    requested_paths: &[PathBuf],
    archive_after_days: u64,
    confirmed: bool,
) -> Result<MemoryArchiveResult, MemoryIndexError> {
    let discovery = discover_memory(repository_root);
    if let Some(diagnostic) = discovery.diagnostics.first() {
        return Err(MemoryIndexError::Archive(format!(
            "cannot plan while {} is invalid: {}",
            diagnostic.repository_relative_path, diagnostic.message
        )));
    }
    let moves = if requested_paths.is_empty() {
        automatic_moves(
            repository_root,
            &discovery.documents,
            archive_after_days,
            SystemTime::now(),
        )?
    } else {
        explicit_moves(
            repository_root,
            &discovery.documents,
            requested_paths,
            confirmed,
        )?
    };
    validate_moves(&moves)?;
    publish_moves(&moves)?;
    if moves.is_empty() {
        return Ok(MemoryArchiveResult {
            moves: Vec::new(),
            sync: None,
        });
    }
    let sync = match crate::engine::main::sync_memory_index::sync_memory_index(
        repository_root,
        database_path,
    ) {
        Ok(summary) => summary,
        Err(error) => {
            rollback_moves(&moves).map_err(|rollback| {
                MemoryIndexError::Archive(format!(
                    "{error}; source rollback also failed: {rollback}"
                ))
            })?;
            return Err(error);
        }
    };
    Ok(MemoryArchiveResult {
        moves: moves
            .into_iter()
            .map(|planned| MemoryArchiveMove {
                source: planned.source_relative,
                destination: planned.destination_relative,
            })
            .collect(),
        sync: Some(sync),
    })
}

fn automatic_moves(
    repository_root: &Path,
    documents: &[DiscoveredDocument],
    archive_after_days: u64,
    now: SystemTime,
) -> Result<Vec<PlannedMove>, MemoryIndexError> {
    if archive_after_days == 0 {
        return Ok(Vec::new());
    }
    let mut moves = Vec::new();
    for document in documents {
        if document.canonical_path.archive_state == ArchiveState::Active
            && terminal_lifecycle(document.lifecycle)
            && old_enough(&document.metadata, now, archive_after_days)?
        {
            moves.push(document_move(repository_root, document)?);
        }
    }
    Ok(moves)
}

fn explicit_moves(
    repository_root: &Path,
    documents: &[DiscoveredDocument],
    requested_paths: &[PathBuf],
    confirmed: bool,
) -> Result<Vec<PlannedMove>, MemoryIndexError> {
    let indexed = explicit_index(documents);
    let mut moves: BTreeMap<PathBuf, PlannedMove> = BTreeMap::new();
    for requested in requested_paths {
        let normalized = normalize_requested_path(requested)?;
        let document = indexed.get(&normalized).ok_or_else(|| {
            MemoryIndexError::Archive(format!(
                "explicit path is not one canonical document or skill bundle: {}",
                normalized.display()
            ))
        })?;
        validate_explicit_document(document, confirmed)?;
        let planned = document_move(repository_root, document)?;
        moves.insert(planned.source_path.clone(), planned);
    }
    Ok(moves.into_values().collect())
}

fn explicit_index(documents: &[DiscoveredDocument]) -> BTreeMap<PathBuf, &DiscoveredDocument> {
    let mut indexed = BTreeMap::new();
    for document in documents {
        let path = PathBuf::from(&document.canonical_path.repository_relative);
        indexed.insert(path.clone(), document);
        if document.artifact_kind == ArtifactKind::Skill {
            if let Some(parent) = path.parent() {
                indexed.insert(parent.to_path_buf(), document);
            }
        }
    }
    indexed
}

fn validate_explicit_document(
    document: &DiscoveredDocument,
    confirmed: bool,
) -> Result<(), MemoryIndexError> {
    if document.canonical_path.archive_state == ArchiveState::Archived {
        return Err(MemoryIndexError::Archive(format!(
            "source is already archived: {}",
            document.canonical_path.repository_relative
        )));
    }
    if document.artifact_kind != ArtifactKind::Task {
        return Ok(());
    }
    if !terminal_lifecycle(document.lifecycle) {
        return Err(MemoryIndexError::Archive(format!(
            "active task must move to completed, cancelled, or superseded before archival: {}",
            document.canonical_path.repository_relative
        )));
    }
    if !confirmed {
        return Err(MemoryIndexError::Archive(format!(
            "explicit terminal task archival requires --yes: {}",
            document.canonical_path.repository_relative
        )));
    }
    Ok(())
}

fn terminal_lifecycle(lifecycle: Option<TaskLifecycle>) -> bool {
    matches!(
        lifecycle,
        Some(TaskLifecycle::Completed | TaskLifecycle::Cancelled | TaskLifecycle::Superseded)
    )
}

fn old_enough(
    metadata: &SourceMetadata,
    now: SystemTime,
    archive_after_days: u64,
) -> Result<bool, MemoryIndexError> {
    let latest = metadata
        .changed_at
        .map(|changed| changed.max(metadata.modified_at))
        .unwrap_or(metadata.modified_at);
    let age = now.duration_since(latest).unwrap_or_default();
    let cutoff = archive_after_days
        .checked_mul(SECONDS_PER_DAY)
        .ok_or_else(|| {
            MemoryIndexError::Archive("archive age exceeds supported range".to_owned())
        })?;
    Ok(age >= Duration::from_secs(cutoff))
}

fn document_move(
    repository_root: &Path,
    document: &DiscoveredDocument,
) -> Result<PlannedMove, MemoryIndexError> {
    let source_relative = PathBuf::from(&document.canonical_path.repository_relative);
    let (source_relative, destination_relative) = if document.artifact_kind == ArtifactKind::Skill {
        let bundle = source_relative.parent().ok_or_else(|| {
            MemoryIndexError::Archive("skill document has no bundle root".to_owned())
        })?;
        (
            bundle.to_path_buf(),
            Path::new(".ai/_archive").join(bundle.strip_prefix(".ai").map_err(|_| {
                MemoryIndexError::Archive("skill path is outside the memory root".to_owned())
            })?),
        )
    } else {
        let suffix = source_relative.strip_prefix(".ai").map_err(|_| {
            MemoryIndexError::Archive("document path is outside the memory root".to_owned())
        })?;
        (
            source_relative.clone(),
            Path::new(".ai/_archive").join(suffix),
        )
    };
    Ok(PlannedMove {
        source_path: repository_root.join(&source_relative),
        destination_path: repository_root.join(&destination_relative),
        source_relative: to_posix(&source_relative),
        destination_relative: to_posix(&destination_relative),
    })
}

fn normalize_requested_path(path: &Path) -> Result<PathBuf, MemoryIndexError> {
    if path.is_absolute()
        || path
            .components()
            .any(|component| !matches!(component, Component::Normal(_)))
    {
        return Err(MemoryIndexError::Archive(format!(
            "explicit path must be repository-relative without traversal: {}",
            path.display()
        )));
    }
    Ok(path.to_path_buf())
}

fn validate_moves(moves: &[PlannedMove]) -> Result<(), MemoryIndexError> {
    for planned in moves {
        if !planned.source_path.exists() {
            return Err(MemoryIndexError::Archive(format!(
                "source no longer exists: {}",
                planned.source_relative
            )));
        }
        if planned.destination_path.exists() {
            return Err(MemoryIndexError::Archive(format!(
                "archive destination already exists: {}",
                planned.destination_relative
            )));
        }
    }
    Ok(())
}

fn publish_moves(moves: &[PlannedMove]) -> Result<(), MemoryIndexError> {
    let mut published = Vec::new();
    for planned in moves {
        if let Some(parent) = planned.destination_path.parent() {
            fs::create_dir_all(parent).map_err(|source| {
                MemoryIndexError::filesystem(
                    "create archive directory",
                    parent.to_path_buf(),
                    source,
                )
            })?;
        }
        if let Err(source) = fs::rename(&planned.source_path, &planned.destination_path) {
            rollback_moves(&published).map_err(|rollback| {
                MemoryIndexError::Archive(format!(
                    "move {} failed: {source}; rollback also failed: {rollback}",
                    planned.source_relative
                ))
            })?;
            return Err(MemoryIndexError::filesystem(
                "archive memory source",
                planned.source_path.clone(),
                source,
            ));
        }
        published.push(planned.clone());
    }
    Ok(())
}

fn rollback_moves(moves: &[PlannedMove]) -> Result<(), String> {
    for planned in moves.iter().rev() {
        if let Some(parent) = planned.source_path.parent() {
            fs::create_dir_all(parent).map_err(|error| error.to_string())?;
        }
        fs::rename(&planned.destination_path, &planned.source_path)
            .map_err(|error| error.to_string())?;
    }
    Ok(())
}

fn to_posix(path: &Path) -> String {
    path.components()
        .map(|component| component.as_os_str().to_string_lossy())
        .collect::<Vec<_>>()
        .join("/")
}
