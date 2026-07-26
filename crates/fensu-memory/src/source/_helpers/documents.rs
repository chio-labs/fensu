//! Timestamped task, note, and decision document discovery.

use std::path::Path;

use crate::source::_helpers::{filesystem, validation};
use crate::source::constants;
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

pub(crate) struct DocumentDirectoryRequest<'a> {
    pub(crate) repository_root: &'a Path,
    pub(crate) directory: &'a Path,
    pub(crate) artifact_kind: ArtifactKind,
    pub(crate) lifecycle: Option<TaskLifecycle>,
    pub(crate) archive_state: ArchiveState,
    pub(crate) result: &'a mut DiscoveryResult,
}

struct DocumentAppendRequest<'a> {
    repository_root: &'a Path,
    path: &'a Path,
    basename: String,
    classification: DocumentClassification,
    parsed: ParsedDocumentName,
    result: &'a mut DiscoveryResult,
}

struct DiagnosticAppender<'a> {
    repository_root: &'a Path,
    diagnostics: &'a mut Vec<DiscoveryDiagnostic>,
}

pub(crate) fn scan_document_directory(request: DocumentDirectoryRequest<'_>) {
    let DocumentDirectoryRequest {
        repository_root,
        directory,
        artifact_kind,
        lifecycle,
        archive_state,
        result,
    } = request;
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
            Ok(parsed) => append_document(DocumentAppendRequest {
                repository_root,
                path: &entry.path(),
                basename,
                classification,
                parsed,
                result,
            }),
            Err(kind) => result.diagnostics.push(filesystem::diagnostic(
                repository_root,
                &entry.path(),
                kind,
                format!("invalid canonical {artifact_kind:?} filename"),
            )),
        }
    }
}

fn append_document(request: DocumentAppendRequest<'_>) {
    let DocumentAppendRequest {
        repository_root,
        path,
        basename,
        classification,
        parsed,
        result,
    } = request;
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
    DiagnosticAppender {
        repository_root,
        diagnostics,
    }
    .unknown_entry(path);
}

impl DiagnosticAppender<'_> {
    fn unknown_entry(&mut self, path: &Path) {
        self.diagnostics.push(filesystem::diagnostic(
            self.repository_root,
            path,
            DiagnosticKind::UnknownStructuralEntry,
            "entry is not part of the canonical memory tree".to_owned(),
        ));
    }
}
