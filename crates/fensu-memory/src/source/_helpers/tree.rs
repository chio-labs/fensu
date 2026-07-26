//! Canonical active and archive tree classification.

use std::fs::{DirEntry, FileType};
use std::path::Path;

use crate::source::_helpers::{documents, filesystem, skills, validation};
use crate::source::constants;
use crate::source::models::DiscoveryResult;
use crate::source::types::{ArchiveState, ArtifactKind, DiagnosticKind};

pub(crate) fn walk_repository(repository_root: &Path) -> DiscoveryResult {
    let mut result = DiscoveryResult::default();
    RepositoryScanner {
        repository_root,
        result: &mut result,
    }
    .scan_memory_root(&repository_root.join(constants::MEMORY_ROOT));
    result
}

struct RepositoryScanner<'a> {
    repository_root: &'a Path,
    result: &'a mut DiscoveryResult,
}

impl RepositoryScanner<'_> {
    fn scan_memory_root(&mut self, directory: &Path) {
        let entries = filesystem::sorted_directory_entries(
            self.repository_root,
            directory,
            &mut self.result.diagnostics,
        );
        for entry in entries {
            let Some((name, file_type)) = self.classified_entry(&entry) else {
                continue;
            };
            match (name.as_str(), file_type.is_dir()) {
                (constants::TASKS_DIRECTORY, true) => {
                    self.scan_tasks(&entry.path(), ArchiveState::Active)
                }
                (constants::KNOWLEDGE_DIRECTORY, true) => {
                    self.scan_knowledge(&entry.path(), ArchiveState::Active)
                }
                (constants::ARCHIVE_DIRECTORY, true) => self.scan_archive(&entry.path()),
                (_, _) => self.append_root_entry_diagnostic(&entry, &name, file_type.is_file()),
            }
        }
    }

    fn scan_tasks(&mut self, directory: &Path, archive_state: ArchiveState) {
        let entries = filesystem::sorted_directory_entries(
            self.repository_root,
            directory,
            &mut self.result.diagnostics,
        );
        for entry in entries {
            let Some((name, file_type)) = self.classified_entry(&entry) else {
                continue;
            };
            let lifecycle = match archive_state {
                ArchiveState::Active => validation::active_lifecycle(&name),
                ArchiveState::Archived => validation::archived_lifecycle(&name),
            };
            match (lifecycle, file_type.is_dir()) {
                (Some(lifecycle), true) => {
                    documents::scan_document_directory(documents::DocumentDirectoryRequest {
                        repository_root: self.repository_root,
                        directory: &entry.path(),
                        artifact_kind: ArtifactKind::Task,
                        lifecycle: Some(lifecycle),
                        archive_state,
                        result: self.result,
                    })
                }
                _ => documents::unknown_entry(
                    self.repository_root,
                    &entry.path(),
                    &mut self.result.diagnostics,
                ),
            }
        }
    }

    fn scan_knowledge(&mut self, directory: &Path, archive_state: ArchiveState) {
        let entries = filesystem::sorted_directory_entries(
            self.repository_root,
            directory,
            &mut self.result.diagnostics,
        );
        for entry in entries {
            let Some((name, file_type)) = self.classified_entry(&entry) else {
                continue;
            };
            match (name.as_str(), file_type.is_dir()) {
                (constants::REPOSITORY_DIRECTORY, true) => {
                    self.scan_repository_knowledge(&entry.path(), archive_state)
                }
                (_, _) => documents::unknown_entry(
                    self.repository_root,
                    &entry.path(),
                    &mut self.result.diagnostics,
                ),
            }
        }
    }

    fn scan_repository_knowledge(&mut self, directory: &Path, archive_state: ArchiveState) {
        let entries = filesystem::sorted_directory_entries(
            self.repository_root,
            directory,
            &mut self.result.diagnostics,
        );
        for entry in entries {
            let Some((name, file_type)) = self.classified_entry(&entry) else {
                continue;
            };
            match (name.as_str(), file_type.is_dir()) {
                (constants::NOTES_DIRECTORY, true) => {
                    documents::scan_document_directory(documents::DocumentDirectoryRequest {
                        repository_root: self.repository_root,
                        directory: &entry.path(),
                        artifact_kind: ArtifactKind::Note,
                        lifecycle: None,
                        archive_state,
                        result: self.result,
                    })
                }
                (constants::DECISIONS_DIRECTORY, true) => {
                    documents::scan_document_directory(documents::DocumentDirectoryRequest {
                        repository_root: self.repository_root,
                        directory: &entry.path(),
                        artifact_kind: ArtifactKind::Decision,
                        lifecycle: None,
                        archive_state,
                        result: self.result,
                    })
                }
                (constants::SKILLS_DIRECTORY, true) => skills::scan_skills_directory(
                    self.repository_root,
                    &entry.path(),
                    archive_state,
                    self.result,
                ),
                (_, _) => documents::unknown_entry(
                    self.repository_root,
                    &entry.path(),
                    &mut self.result.diagnostics,
                ),
            }
        }
    }

    fn scan_archive(&mut self, directory: &Path) {
        let entries = filesystem::sorted_directory_entries(
            self.repository_root,
            directory,
            &mut self.result.diagnostics,
        );
        for entry in entries {
            let Some((name, file_type)) = self.classified_entry(&entry) else {
                continue;
            };
            match (name.as_str(), file_type.is_dir()) {
                (constants::TASKS_DIRECTORY, true) => {
                    self.scan_tasks(&entry.path(), ArchiveState::Archived)
                }
                (constants::KNOWLEDGE_DIRECTORY, true) => {
                    self.scan_knowledge(&entry.path(), ArchiveState::Archived)
                }
                (_, _) => documents::unknown_entry(
                    self.repository_root,
                    &entry.path(),
                    &mut self.result.diagnostics,
                ),
            }
        }
    }

    fn classified_entry(&mut self, entry: &DirEntry) -> Option<(String, FileType)> {
        let file_type =
            filesystem::entry_type(self.repository_root, entry, &mut self.result.diagnostics)?;
        if file_type.is_symlink() {
            self.result.diagnostics.push(filesystem::diagnostic(
                self.repository_root,
                &entry.path(),
                DiagnosticKind::SymlinkRejected,
                "canonical structural entry is a symlink".to_owned(),
            ));
            return None;
        }
        let name =
            filesystem::entry_name(self.repository_root, entry, &mut self.result.diagnostics)?;
        Some((name, file_type))
    }

    fn append_root_entry_diagnostic(&mut self, entry: &DirEntry, name: &str, is_file: bool) {
        let kind = match is_file && name.ends_with(constants::MARKDOWN_SUFFIX) {
            true => DiagnosticKind::RootMarkdown,
            false => DiagnosticKind::UnknownStructuralEntry,
        };
        self.result.diagnostics.push(filesystem::diagnostic(
            self.repository_root,
            &entry.path(),
            kind,
            "root entry is not part of the canonical memory tree".to_owned(),
        ));
    }
}
