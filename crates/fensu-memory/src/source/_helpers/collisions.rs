//! Duplicate identity, basename, and portable case-collision detection.

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use crate::source::_helpers::filesystem;
use crate::source::models::DiscoveryResult;
use crate::source::types::{ArtifactKind, DiagnosticKind};

pub(crate) fn append_collision_diagnostics(repository_root: &Path, result: &mut DiscoveryResult) {
    CollisionAnalysis {
        repository_root,
        result,
    }
    .append();
}

struct CollisionAnalysis<'a> {
    repository_root: &'a Path,
    result: &'a mut DiscoveryResult,
}

impl CollisionAnalysis<'_> {
    fn append(mut self) {
        self.append_identity_collisions();
        self.append_basename_collisions();
        self.append_case_collisions();
    }

    fn append_identity_collisions(&mut self) {
        let mut groups: BTreeMap<String, Vec<String>> = BTreeMap::new();
        for document in &self.result.documents {
            groups
                .entry(document.identity.0.clone())
                .or_default()
                .push(document.canonical_path.repository_relative.clone());
        }
        self.append_duplicate_groups(
            groups,
            DiagnosticKind::DuplicateIdentity,
            "document identity appears at multiple canonical paths",
        );
    }

    fn append_basename_collisions(&mut self) {
        let mut groups: BTreeMap<String, Vec<String>> = BTreeMap::new();
        for document in self
            .result
            .documents
            .iter()
            .filter(|document| document.artifact_kind != ArtifactKind::Skill)
        {
            groups
                .entry(document.basename.clone())
                .or_default()
                .push(document.canonical_path.repository_relative.clone());
        }
        self.append_duplicate_groups(
            groups,
            DiagnosticKind::DuplicateBasename,
            "document basename appears at multiple canonical paths",
        );
    }

    fn append_case_collisions(&mut self) {
        let mut groups: BTreeMap<String, Vec<(String, String)>> = BTreeMap::new();
        for document in &self.result.documents {
            let path = document.canonical_path.repository_relative.clone();
            groups
                .entry(path.to_lowercase())
                .or_default()
                .push((path.clone(), path));
        }
        for skill_file in &self.result.skill_files {
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
                self.result.diagnostics.push(filesystem::diagnostic(
                    self.repository_root,
                    &self.repository_root.join(path),
                    DiagnosticKind::CaseFoldCollision,
                    "canonical source paths differ only by case".to_owned(),
                ));
            }
        }
    }

    fn append_duplicate_groups(
        &mut self,
        groups: BTreeMap<String, Vec<String>>,
        kind: DiagnosticKind,
        message: &str,
    ) {
        for paths in groups.values().filter(|paths| paths.len() > 1) {
            for path in paths {
                self.result.diagnostics.push(filesystem::diagnostic(
                    self.repository_root,
                    &self.repository_root.join(path),
                    kind,
                    message.to_owned(),
                ));
            }
        }
    }
}
