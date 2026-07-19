//! Skill document and nested regular support-file discovery.

use std::path::Path;

use crate::source::constants;
use crate::source::helpers::{filesystem, validation};
use crate::source::models::{
    CanonicalPath, DiscoveredDocument, DiscoveredSkillFile, DiscoveryResult, DocumentIdentity,
};
use crate::source::types::{ArchiveState, ArtifactKind, DiagnosticKind, GitTracking};

pub(crate) fn scan_skills_directory(
    repository_root: &Path,
    directory: &Path,
    archive_state: ArchiveState,
    result: &mut DiscoveryResult,
) {
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
                "skill bundle is a symlink".to_owned(),
            ));
            continue;
        }
        let Some(skill_name) =
            filesystem::entry_name(repository_root, &entry, &mut result.diagnostics)
        else {
            continue;
        };
        if !file_type.is_dir() {
            result.diagnostics.push(filesystem::diagnostic(
                repository_root,
                &entry.path(),
                DiagnosticKind::UnknownStructuralEntry,
                "skills directory entries must be named bundle directories".to_owned(),
            ));
            continue;
        }
        match validation::validate_skill_name(&skill_name) {
            Ok(()) => scan_skill_bundle(
                repository_root,
                &entry.path(),
                &skill_name,
                archive_state,
                result,
            ),
            Err(kind) => result.diagnostics.push(filesystem::diagnostic(
                repository_root,
                &entry.path(),
                kind,
                "skill name must be ASCII kebab-case".to_owned(),
            )),
        }
    }
}

fn scan_skill_bundle(
    repository_root: &Path,
    bundle_root: &Path,
    skill_name: &str,
    archive_state: ArchiveState,
    result: &mut DiscoveryResult,
) {
    let identity = DocumentIdentity(format!(
        "skill{}{}",
        constants::IDENTITY_SEPARATOR,
        skill_name
    ));
    let document_path = bundle_root.join(constants::SKILL_DOCUMENT);
    let first_skill_file = result.skill_files.len();
    scan_skill_files(
        repository_root,
        bundle_root,
        bundle_root,
        &identity,
        archive_state,
        result,
    );
    if !result
        .documents
        .iter()
        .any(|document| document.canonical_path.filesystem_path == document_path)
    {
        result.skill_files.truncate(first_skill_file);
        result.diagnostics.push(filesystem::diagnostic(
            repository_root,
            &document_path,
            DiagnosticKind::MissingSkillDocument,
            "skill bundle has no regular SKILL.md document".to_owned(),
        ));
    }
}

fn scan_skill_files(
    repository_root: &Path,
    bundle_root: &Path,
    directory: &Path,
    identity: &DocumentIdentity,
    archive_state: ArchiveState,
    result: &mut DiscoveryResult,
) {
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
                "skill content is a symlink".to_owned(),
            ));
            continue;
        }
        if file_type.is_dir() {
            scan_skill_files(
                repository_root,
                bundle_root,
                &entry.path(),
                identity,
                archive_state,
                result,
            );
            continue;
        }
        if !file_type.is_file() {
            result.diagnostics.push(filesystem::diagnostic(
                repository_root,
                &entry.path(),
                DiagnosticKind::UnsupportedFileType,
                "skill content is not a regular file".to_owned(),
            ));
            continue;
        }
        let is_document = entry.path() == bundle_root.join(constants::SKILL_DOCUMENT);
        match is_document {
            true => append_skill_document(
                repository_root,
                &entry.path(),
                identity,
                archive_state,
                result,
            ),
            false => append_skill_file(
                repository_root,
                bundle_root,
                &entry.path(),
                identity,
                archive_state,
                result,
            ),
        }
    }
}

fn append_skill_document(
    repository_root: &Path,
    path: &Path,
    identity: &DocumentIdentity,
    archive_state: ArchiveState,
    result: &mut DiscoveryResult,
) {
    let Some((metadata, repository_relative)) =
        loaded_file(repository_root, path, &mut result.diagnostics)
    else {
        return;
    };
    let slug = identity
        .0
        .strip_prefix("skill:")
        .unwrap_or_default()
        .to_owned();
    result.documents.push(DiscoveredDocument {
        identity: identity.clone(),
        artifact_kind: ArtifactKind::Skill,
        task_category: None,
        lifecycle: None,
        canonical_path: CanonicalPath {
            filesystem_path: path.to_path_buf(),
            repository_relative,
            archive_state,
        },
        basename: constants::SKILL_DOCUMENT.to_owned(),
        slug,
        creation_timestamp: None,
        metadata,
        git_tracking: GitTracking::Unavailable,
    });
}

fn append_skill_file(
    repository_root: &Path,
    bundle_root: &Path,
    path: &Path,
    identity: &DocumentIdentity,
    archive_state: ArchiveState,
    result: &mut DiscoveryResult,
) {
    let Some((metadata, repository_relative)) =
        loaded_file(repository_root, path, &mut result.diagnostics)
    else {
        return;
    };
    let bundle_relative_path = match filesystem::portable_path(bundle_root, path) {
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
    result.skill_files.push(DiscoveredSkillFile {
        skill_identity: identity.clone(),
        canonical_path: CanonicalPath {
            filesystem_path: path.to_path_buf(),
            repository_relative,
            archive_state,
        },
        bundle_relative_path,
        metadata,
        git_tracking: GitTracking::Unavailable,
    });
}

fn loaded_file(
    repository_root: &Path,
    path: &Path,
    diagnostics: &mut Vec<crate::source::models::DiscoveryDiagnostic>,
) -> Option<(crate::source::models::SourceMetadata, String)> {
    let metadata = match filesystem::source_metadata(path) {
        Ok(metadata) => metadata,
        Err(error) => {
            diagnostics.push(filesystem::diagnostic(
                repository_root,
                path,
                DiagnosticKind::Io,
                format!("cannot read skill content: {error}"),
            ));
            return None;
        }
    };
    let repository_relative = match filesystem::portable_path(repository_root, path) {
        Ok(relative) => relative,
        Err(error) => {
            diagnostics.push(filesystem::diagnostic(
                repository_root,
                path,
                DiagnosticKind::InvalidPathEncoding,
                error,
            ));
            return None;
        }
    };
    Some((metadata, repository_relative))
}
