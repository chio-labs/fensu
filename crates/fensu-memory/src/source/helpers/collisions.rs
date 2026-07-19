//! Duplicate identity, basename, and portable case-collision detection.

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use crate::source::helpers::filesystem;
use crate::source::models::{DiscoveredDocument, DiscoveryResult};
use crate::source::types::{ArtifactKind, DiagnosticKind};

pub(crate) fn append_collision_diagnostics(repository_root: &Path, result: &mut DiscoveryResult) {
    append_identity_collisions(repository_root, result);
    append_basename_collisions(repository_root, result);
    append_case_collisions(repository_root, result);
}

fn append_identity_collisions(repository_root: &Path, result: &mut DiscoveryResult) {
    let mut groups: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for document in &result.documents {
        groups
            .entry(document.identity.0.clone())
            .or_default()
            .push(document.canonical_path.repository_relative.clone());
    }
    append_duplicate_groups(
        repository_root,
        groups,
        DiagnosticKind::DuplicateIdentity,
        "document identity appears at multiple canonical paths",
        result,
    );
}

fn append_basename_collisions(repository_root: &Path, result: &mut DiscoveryResult) {
    let mut groups: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for document in result
        .documents
        .iter()
        .filter(|document| document.artifact_kind != ArtifactKind::Skill)
    {
        groups
            .entry(document.basename.clone())
            .or_default()
            .push(document.canonical_path.repository_relative.clone());
    }
    append_duplicate_groups(
        repository_root,
        groups,
        DiagnosticKind::DuplicateBasename,
        "document basename appears at multiple canonical paths",
        result,
    );
}

fn append_case_collisions(repository_root: &Path, result: &mut DiscoveryResult) {
    let mut groups: BTreeMap<String, Vec<(String, String)>> = BTreeMap::new();
    for document in &result.documents {
        append_case_candidate(&mut groups, document);
    }
    for skill_file in &result.skill_files {
        let path = skill_file.canonical_path.repository_relative.clone();
        groups
            .entry(path.to_lowercase())
            .or_default()
            .push((path.clone(), path));
    }
    for candidates in groups.values() {
        let spellings: BTreeSet<&str> = candidates
            .iter()
            .map(|(spelling, _)| spelling.as_str())
            .collect();
        if spellings.len() <= 1 {
            continue;
        }
        for (_, path) in candidates {
            result.diagnostics.push(filesystem::diagnostic(
                repository_root,
                &repository_root.join(path),
                DiagnosticKind::CaseFoldCollision,
                "canonical source paths differ only by case".to_owned(),
            ));
        }
    }
}

fn append_case_candidate(
    groups: &mut BTreeMap<String, Vec<(String, String)>>,
    document: &DiscoveredDocument,
) {
    let path = document.canonical_path.repository_relative.clone();
    groups
        .entry(path.to_lowercase())
        .or_default()
        .push((path.clone(), path));
}

fn append_duplicate_groups(
    repository_root: &Path,
    groups: BTreeMap<String, Vec<String>>,
    kind: DiagnosticKind,
    message: &str,
    result: &mut DiscoveryResult,
) {
    for paths in groups.values().filter(|paths| paths.len() > 1) {
        for path in paths {
            result.diagnostics.push(filesystem::diagnostic(
                repository_root,
                &repository_root.join(path),
                kind,
                message.to_owned(),
            ));
        }
    }
}
