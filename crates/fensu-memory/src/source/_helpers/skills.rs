//! Skill document and nested regular support-file discovery.

use std::path::Path;

use crate::source::_helpers::{filesystem, validation};
use crate::source::constants;
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
    SkillScanner {
        repository_root,
        archive_state,
        result,
    }
    .scan_directory(directory);
}

struct SkillScanner<'a> {
    repository_root: &'a Path,
    archive_state: ArchiveState,
    result: &'a mut DiscoveryResult,
}

impl SkillScanner<'_> {
    fn scan_directory(&mut self, directory: &Path) {
        let entries = filesystem::sorted_directory_entries(
            self.repository_root,
            directory,
            &mut self.result.diagnostics,
        );
        for entry in entries {
            let Some(file_type) =
                filesystem::entry_type(self.repository_root, &entry, &mut self.result.diagnostics)
            else {
                continue;
            };
            if file_type.is_symlink() {
                self.result.diagnostics.push(filesystem::diagnostic(
                    self.repository_root,
                    &entry.path(),
                    DiagnosticKind::SymlinkRejected,
                    "skill bundle is a symlink".to_owned(),
                ));
                continue;
            }
            let Some(skill_name) =
                filesystem::entry_name(self.repository_root, &entry, &mut self.result.diagnostics)
            else {
                continue;
            };
            if !file_type.is_dir() {
                self.result.diagnostics.push(filesystem::diagnostic(
                    self.repository_root,
                    &entry.path(),
                    DiagnosticKind::UnknownStructuralEntry,
                    "skills directory entries must be named bundle directories".to_owned(),
                ));
                continue;
            }
            match validation::validate_skill_name(&skill_name) {
                Ok(()) => self.scan_skill_bundle(&entry.path(), &skill_name),
                Err(kind) => self.result.diagnostics.push(filesystem::diagnostic(
                    self.repository_root,
                    &entry.path(),
                    kind,
                    "skill name must be ASCII kebab-case".to_owned(),
                )),
            }
        }
    }

    fn scan_skill_bundle(&mut self, bundle_root: &Path, skill_name: &str) {
        let identity = DocumentIdentity(format!(
            "skill{}{}",
            constants::IDENTITY_SEPARATOR,
            skill_name
        ));
        let document_path = bundle_root.join(constants::SKILL_DOCUMENT);
        let first_skill_file = self.result.skill_files.len();
        self.scan_skill_files(bundle_root, bundle_root, &identity);
        if !self
            .result
            .documents
            .iter()
            .any(|document| document.canonical_path.filesystem_path == document_path)
        {
            self.result.skill_files.truncate(first_skill_file);
            self.result.diagnostics.push(filesystem::diagnostic(
                self.repository_root,
                &document_path,
                DiagnosticKind::MissingSkillDocument,
                "skill bundle has no regular SKILL.md document".to_owned(),
            ));
        }
    }

    fn scan_skill_files(
        &mut self,
        bundle_root: &Path,
        directory: &Path,
        identity: &DocumentIdentity,
    ) {
        let entries = filesystem::sorted_directory_entries(
            self.repository_root,
            directory,
            &mut self.result.diagnostics,
        );
        for entry in entries {
            let Some(file_type) =
                filesystem::entry_type(self.repository_root, &entry, &mut self.result.diagnostics)
            else {
                continue;
            };
            if file_type.is_symlink() {
                self.result.diagnostics.push(filesystem::diagnostic(
                    self.repository_root,
                    &entry.path(),
                    DiagnosticKind::SymlinkRejected,
                    "skill content is a symlink".to_owned(),
                ));
                continue;
            }
            if file_type.is_dir() {
                self.scan_skill_files(bundle_root, &entry.path(), identity);
                continue;
            }
            if !file_type.is_file() {
                self.result.diagnostics.push(filesystem::diagnostic(
                    self.repository_root,
                    &entry.path(),
                    DiagnosticKind::UnsupportedFileType,
                    "skill content is not a regular file".to_owned(),
                ));
                continue;
            }
            let is_document = entry.path() == bundle_root.join(constants::SKILL_DOCUMENT);
            match is_document {
                true => self.append_skill_document(&entry.path(), identity),
                false => self.append_skill_file(bundle_root, &entry.path(), identity),
            }
        }
    }

    fn append_skill_document(&mut self, path: &Path, identity: &DocumentIdentity) {
        let Some((metadata, repository_relative)) = self.loaded_file(path) else {
            return;
        };
        let slug = identity
            .0
            .strip_prefix("skill:")
            .unwrap_or_default()
            .to_owned();
        self.result.documents.push(DiscoveredDocument {
            identity: identity.clone(),
            artifact_kind: ArtifactKind::Skill,
            task_category: None,
            lifecycle: None,
            canonical_path: CanonicalPath {
                filesystem_path: path.to_path_buf(),
                repository_relative,
                archive_state: self.archive_state,
            },
            basename: constants::SKILL_DOCUMENT.to_owned(),
            slug,
            creation_timestamp: None,
            metadata,
            git_tracking: GitTracking::Unavailable,
        });
    }

    fn append_skill_file(&mut self, bundle_root: &Path, path: &Path, identity: &DocumentIdentity) {
        let Some((metadata, repository_relative)) = self.loaded_file(path) else {
            return;
        };
        let bundle_relative_path = match filesystem::portable_path(bundle_root, path) {
            Ok(relative) => relative,
            Err(error) => {
                self.result.diagnostics.push(filesystem::diagnostic(
                    self.repository_root,
                    path,
                    DiagnosticKind::InvalidPathEncoding,
                    error,
                ));
                return;
            }
        };
        self.result.skill_files.push(DiscoveredSkillFile {
            skill_identity: identity.clone(),
            canonical_path: CanonicalPath {
                filesystem_path: path.to_path_buf(),
                repository_relative,
                archive_state: self.archive_state,
            },
            bundle_relative_path,
            metadata,
            git_tracking: GitTracking::Unavailable,
        });
    }

    fn loaded_file(
        &mut self,
        path: &Path,
    ) -> Option<(crate::source::models::SourceMetadata, String)> {
        let metadata = match filesystem::source_metadata(path) {
            Ok(metadata) => metadata,
            Err(error) => {
                self.result.diagnostics.push(filesystem::diagnostic(
                    self.repository_root,
                    path,
                    DiagnosticKind::Io,
                    format!("cannot read skill content: {error}"),
                ));
                return None;
            }
        };
        let repository_relative = match filesystem::portable_path(self.repository_root, path) {
            Ok(relative) => relative,
            Err(error) => {
                self.result.diagnostics.push(filesystem::diagnostic(
                    self.repository_root,
                    path,
                    DiagnosticKind::InvalidPathEncoding,
                    error,
                ));
                return None;
            }
        };
        Some((metadata, repository_relative))
    }
}
