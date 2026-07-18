//! Canonical active and archive tree classification.

use std::fs::{DirEntry, FileType};
use std::path::Path;

use crate::source::constants;
use crate::source::helpers::{documents, filesystem, skills, validation};
use crate::source::models::DiscoveryResult;
use crate::source::types::{ArchiveState, ArtifactKind, DiagnosticKind};

pub(crate) fn walk_repository(repository_root: &Path) -> DiscoveryResult {
    let mut result = DiscoveryResult::default();
    scan_memory_root(
        repository_root,
        &repository_root.join(constants::MEMORY_ROOT),
        &mut result,
    );
    result
}

fn scan_memory_root(repository_root: &Path, directory: &Path, result: &mut DiscoveryResult) {
    let entries =
        filesystem::sorted_directory_entries(repository_root, directory, &mut result.diagnostics);
    for entry in entries {
        let Some((name, file_type)) = classified_entry(repository_root, &entry, result) else {
            continue;
        };
        match (name.as_str(), file_type.is_dir()) {
            (constants::TASKS_DIRECTORY, true) => {
                scan_tasks(repository_root, &entry.path(), ArchiveState::Active, result)
            }
            (constants::KNOWLEDGE_DIRECTORY, true) => {
                scan_knowledge(repository_root, &entry.path(), ArchiveState::Active, result)
            }
            (constants::ARCHIVE_DIRECTORY, true) => {
                scan_archive(repository_root, &entry.path(), result)
            }
            (_, _) => append_root_entry_diagnostic(
                repository_root,
                &entry,
                &name,
                file_type.is_file(),
                result,
            ),
        }
    }
}

fn scan_tasks(
    repository_root: &Path,
    directory: &Path,
    archive_state: ArchiveState,
    result: &mut DiscoveryResult,
) {
    let entries =
        filesystem::sorted_directory_entries(repository_root, directory, &mut result.diagnostics);
    for entry in entries {
        let Some((name, file_type)) = classified_entry(repository_root, &entry, result) else {
            continue;
        };
        let lifecycle = match archive_state {
            ArchiveState::Active => validation::active_lifecycle(&name),
            ArchiveState::Archived => validation::archived_lifecycle(&name),
        };
        match (lifecycle, file_type.is_dir()) {
            (Some(lifecycle), true) => documents::scan_document_directory(
                repository_root,
                &entry.path(),
                ArtifactKind::Task,
                Some(lifecycle),
                archive_state,
                result,
            ),
            _ => documents::unknown_entry(repository_root, &entry.path(), &mut result.diagnostics),
        }
    }
}

fn scan_knowledge(
    repository_root: &Path,
    directory: &Path,
    archive_state: ArchiveState,
    result: &mut DiscoveryResult,
) {
    let entries =
        filesystem::sorted_directory_entries(repository_root, directory, &mut result.diagnostics);
    for entry in entries {
        let Some((name, file_type)) = classified_entry(repository_root, &entry, result) else {
            continue;
        };
        match (name.as_str(), file_type.is_dir()) {
            (constants::REPOSITORY_DIRECTORY, true) => {
                scan_repository_knowledge(repository_root, &entry.path(), archive_state, result)
            }
            (_, _) => {
                documents::unknown_entry(repository_root, &entry.path(), &mut result.diagnostics)
            }
        }
    }
}

fn scan_repository_knowledge(
    repository_root: &Path,
    directory: &Path,
    archive_state: ArchiveState,
    result: &mut DiscoveryResult,
) {
    let entries =
        filesystem::sorted_directory_entries(repository_root, directory, &mut result.diagnostics);
    for entry in entries {
        let Some((name, file_type)) = classified_entry(repository_root, &entry, result) else {
            continue;
        };
        match (name.as_str(), file_type.is_dir()) {
            (constants::NOTES_DIRECTORY, true) => documents::scan_document_directory(
                repository_root,
                &entry.path(),
                ArtifactKind::Note,
                None,
                archive_state,
                result,
            ),
            (constants::DECISIONS_DIRECTORY, true) => documents::scan_document_directory(
                repository_root,
                &entry.path(),
                ArtifactKind::Decision,
                None,
                archive_state,
                result,
            ),
            (constants::SKILLS_DIRECTORY, true) => {
                skills::scan_skills_directory(repository_root, &entry.path(), archive_state, result)
            }
            (_, _) => {
                documents::unknown_entry(repository_root, &entry.path(), &mut result.diagnostics)
            }
        }
    }
}

fn scan_archive(repository_root: &Path, directory: &Path, result: &mut DiscoveryResult) {
    let entries =
        filesystem::sorted_directory_entries(repository_root, directory, &mut result.diagnostics);
    for entry in entries {
        let Some((name, file_type)) = classified_entry(repository_root, &entry, result) else {
            continue;
        };
        match (name.as_str(), file_type.is_dir()) {
            (constants::TASKS_DIRECTORY, true) => scan_tasks(
                repository_root,
                &entry.path(),
                ArchiveState::Archived,
                result,
            ),
            (constants::KNOWLEDGE_DIRECTORY, true) => scan_knowledge(
                repository_root,
                &entry.path(),
                ArchiveState::Archived,
                result,
            ),
            (_, _) => {
                documents::unknown_entry(repository_root, &entry.path(), &mut result.diagnostics)
            }
        }
    }
}

fn classified_entry(
    repository_root: &Path,
    entry: &DirEntry,
    result: &mut DiscoveryResult,
) -> Option<(String, FileType)> {
    let file_type = filesystem::entry_type(repository_root, entry, &mut result.diagnostics)?;
    if file_type.is_symlink() {
        result.diagnostics.push(filesystem::diagnostic(
            repository_root,
            &entry.path(),
            DiagnosticKind::SymlinkRejected,
            "canonical structural entry is a symlink".to_owned(),
        ));
        return None;
    }
    let name = filesystem::entry_name(repository_root, entry, &mut result.diagnostics)?;
    Some((name, file_type))
}

fn append_root_entry_diagnostic(
    repository_root: &Path,
    entry: &DirEntry,
    name: &str,
    is_file: bool,
    result: &mut DiscoveryResult,
) {
    let kind = match is_file && name.ends_with(constants::MARKDOWN_SUFFIX) {
        true => DiagnosticKind::RootMarkdown,
        false => DiagnosticKind::UnknownStructuralEntry,
    };
    result.diagnostics.push(filesystem::diagnostic(
        repository_root,
        &entry.path(),
        kind,
        "root entry is not part of the canonical memory tree".to_owned(),
    ));
}
