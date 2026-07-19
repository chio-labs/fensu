//! Timestamped task, note, and decision document discovery.

use std::path::Path;

use crate::source::constants;
use crate::source::helpers::{filesystem, validation};
use crate::source::models::{
    CanonicalPath, DiscoveredDocument, DiscoveryDiagnostic, DiscoveryResult, DocumentIdentity,
    ParsedDocumentName,
};
use crate::source::types::{
    ArchiveState, ArtifactKind, DiagnosticKind, GitTracking, TaskLifecycle,
};

#[derive(Clone, Copy)]
struct DocumentClassification {
    artifact_kind: ArtifactKind,
    lifecycle: Option<TaskLifecycle>,
    archive_state: ArchiveState,
}

pub(crate) fn scan_document_directory(
    repository_root: &Path,
    directory: &Path,
    artifact_kind: ArtifactKind,
    lifecycle: Option<TaskLifecycle>,
    archive_state: ArchiveState,
    result: &mut DiscoveryResult,
) {
    let classification = DocumentClassification {
        artifact_kind,
        lifecycle,
        archive_state,
    };
    let entries =
        filesystem::sorted_directory_entries(repository_root, directory, &mut result.diagnostics);
    for entry in entries {
        let Some(file_type) =
            filesystem::entry_type(repository_root, &entry, &mut result.diagnostics)
        else {
            continue;
        };
        if file_type.is_symlink() {
            result.diagnostics.push(filesystem::diagnostic(
                repository_root,
                &entry.path(),
                DiagnosticKind::SymlinkRejected,
                "canonical document is a symlink".to_owned(),
            ));
            continue;
        }
        if !file_type.is_file() {
            let kind = match file_type.is_dir() {
                true => DiagnosticKind::UnknownStructuralEntry,
                false => DiagnosticKind::UnsupportedFileType,
            };
            result.diagnostics.push(filesystem::diagnostic(
                repository_root,
                &entry.path(),
                kind,
                "document directory contains a non-document entry".to_owned(),
            ));
            continue;
        }
        let Some(basename) =
            filesystem::entry_name(repository_root, &entry, &mut result.diagnostics)
        else {
            continue;
        };
        match validation::parse_document_name(&basename, artifact_kind) {
            Ok(parsed) => append_document(
                repository_root,
                &entry.path(),
                basename,
                classification,
                parsed,
                result,
            ),
            Err(kind) => result.diagnostics.push(filesystem::diagnostic(
                repository_root,
                &entry.path(),
                kind,
                format!("invalid canonical {artifact_kind:?} filename"),
            )),
        }
    }
}

fn append_document(
    repository_root: &Path,
    path: &Path,
    basename: String,
    classification: DocumentClassification,
    parsed: ParsedDocumentName,
    result: &mut DiscoveryResult,
) {
    let metadata = match filesystem::source_metadata(path) {
        Ok(metadata) => metadata,
        Err(error) => {
            result.diagnostics.push(filesystem::diagnostic(
                repository_root,
                path,
                DiagnosticKind::Io,
                format!("cannot read canonical document: {error}"),
            ));
            return;
        }
    };
    let repository_relative = match filesystem::portable_path(repository_root, path) {
        Ok(relative) => relative,
        Err(error) => {
            result.diagnostics.push(filesystem::diagnostic(
                repository_root,
                path,
                DiagnosticKind::InvalidPathEncoding,
                error,
            ));
            return;
        }
    };
    let identity = DocumentIdentity(format!(
        "{}{}{}",
        identity_kind(classification.artifact_kind),
        constants::IDENTITY_SEPARATOR,
        parsed.timestamp
    ));
    result.documents.push(DiscoveredDocument {
        identity,
        artifact_kind: classification.artifact_kind,
        task_category: parsed.category,
        lifecycle: classification.lifecycle,
        canonical_path: CanonicalPath {
            filesystem_path: path.to_path_buf(),
            repository_relative,
            archive_state: classification.archive_state,
        },
        basename,
        slug: parsed.slug,
        creation_timestamp: Some(parsed.timestamp),
        metadata,
        git_tracking: GitTracking::Unavailable,
    });
}

fn identity_kind(artifact_kind: ArtifactKind) -> &'static str {
    match artifact_kind {
        ArtifactKind::Task => "task",
        ArtifactKind::Note => "note",
        ArtifactKind::Decision => "decision",
        ArtifactKind::Skill => "skill",
    }
}

pub(crate) fn unknown_entry(
    repository_root: &Path,
    path: &Path,
    diagnostics: &mut Vec<DiscoveryDiagnostic>,
) {
    diagnostics.push(filesystem::diagnostic(
        repository_root,
        path,
        DiagnosticKind::UnknownStructuralEntry,
        "entry is not part of the canonical memory tree".to_owned(),
    ));
}
