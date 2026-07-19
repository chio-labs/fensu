//! Single-traversal repository observation index for persistent dependency replay.

use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;

use sha2::{Digest, Sha256};

use crate::snapshot::constants::REPOSITORY_ROOT_PATH;
use crate::snapshot::helpers::observation_index::{glob_matcher, join_relative, traversal_roots};
use crate::snapshot::helpers::repository_paths::{
    repository_relative_value, resolve_allow_missing,
};
use crate::snapshot::models::{
    RepositoryObservationAnswer, RepositoryObservationIndex, RepositoryObservationQuery,
    RepositoryObservationState,
};

impl RepositoryObservationIndex {
    /// Build one shared index while visiting every relevant lexical entry at most once.
    pub fn build(repo_root: &Path, queries: &[RepositoryObservationQuery]) -> Option<Self> {
        let repo_root = dunce::canonicalize(repo_root).ok()?;
        let roots = traversal_roots(&repo_root, queries);
        let mut index = Self {
            repo_root,
            entries: Vec::new(),
            directory_order: Vec::new(),
            direct_entries: HashMap::new(),
            file_paths: HashSet::new(),
            directory_paths: HashSet::new(),
        };
        index.directory_paths.insert(".".to_owned());
        for root in &roots {
            index.walk_root(root);
        }
        index.finalize_order(&roots);
        Some(index)
    }

    /// Return the current state of one supported persisted query.
    pub fn observe(
        &self,
        query: &RepositoryObservationQuery,
    ) -> Option<RepositoryObservationState> {
        let lexical_path = self.repo_root.join(&query.relative_path);
        let resolved_path = resolve_allow_missing(&lexical_path)?;
        let dependency_path = repository_relative_value(&self.repo_root, &resolved_path)?;
        let answer = match query.kind.as_str() {
            "exists" => RepositoryObservationAnswer::Bool(resolved_path.exists()),
            "is_file" => RepositoryObservationAnswer::Bool(resolved_path.is_file()),
            "is_dir" => RepositoryObservationAnswer::Bool(resolved_path.is_dir()),
            "source" => fs::read(lexical_path)
                .ok()
                .map_or(RepositoryObservationAnswer::None, |content| {
                    RepositoryObservationAnswer::String(hex::encode(Sha256::digest(content)))
                }),
            "directory_entries" => RepositoryObservationAnswer::Paths(
                self.direct_entries
                    .get(&query.relative_path)
                    .cloned()
                    .unwrap_or_default(),
            ),
            "python_anchor" => RepositoryObservationAnswer::Paths(
                self.python_anchor(&query.relative_path)
                    .into_iter()
                    .collect(),
            ),
            "glob" => RepositoryObservationAnswer::Paths(self.glob(
                &query.relative_path,
                query.pattern.as_deref()?,
                query.recursive,
            )?),
            _ => return None,
        };
        Some(RepositoryObservationState {
            dependency_path,
            answer,
        })
    }

    fn walk_root(&mut self, root: &Path) {
        let mut pending = vec![root.to_path_buf()];
        while let Some(directory) = pending.pop() {
            let Ok(entries) = fs::read_dir(directory) else {
                continue;
            };
            let mut children = Vec::new();
            for entry in entries.flatten() {
                if entry.file_type().is_ok_and(|kind| kind.is_dir()) {
                    children.push(entry.path());
                }
                self.record_entry(&entry);
            }
            pending.extend(children.into_iter().rev());
        }
    }

    fn record_entry(&mut self, entry: &fs::DirEntry) {
        let entry_path = entry.path();
        let Some(relative) = repository_relative_value(&self.repo_root, &entry_path) else {
            return;
        };
        if relative == REPOSITORY_ROOT_PATH {
            return;
        }
        let Ok(file_type) = entry.file_type() else {
            return;
        };
        if file_type.is_file() || file_type.is_symlink() && entry_path.is_file() {
            self.file_paths.insert(relative.clone());
        }
        if file_type.is_dir() {
            self.directory_paths.insert(relative.clone());
        }
        let parent = entry_path
            .parent()
            .and_then(|path| repository_relative_value(&self.repo_root, path));
        if let Some(parent) = parent {
            self.direct_entries
                .entry(parent)
                .or_default()
                .push(relative);
        }
    }

    fn glob(&self, root: &str, pattern: &str, recursive: bool) -> Option<Vec<String>> {
        let matcher = glob_matcher(pattern)?;
        let starting_points = if recursive {
            self.directory_order
                .iter()
                .filter(|path| is_below(path, root))
                .map(String::as_str)
                .collect::<Vec<_>>()
        } else {
            vec![root]
        };
        if !pattern.contains('/') {
            return Some(self.basename_glob(&starting_points, &matcher));
        }
        let mut matches = Vec::new();
        let mut seen = HashSet::new();
        for starting_point in starting_points {
            for path in &self.entries {
                let Some(relative) = relative_below(path, starting_point) else {
                    continue;
                };
                if matcher.is_match(relative) && seen.insert(path) {
                    matches.push(path.clone());
                }
            }
        }
        Some(matches)
    }

    fn basename_glob(
        &self,
        starting_points: &[&str],
        matcher: &globset::GlobMatcher,
    ) -> Vec<String> {
        starting_points
            .iter()
            .flat_map(|directory| self.direct_entries.get(*directory).into_iter().flatten())
            .filter(|path| {
                let name = path.rsplit_once('/').map(|(_, name)| name).unwrap_or(path);
                matcher.is_match(name)
            })
            .cloned()
            .collect()
    }

    fn finalize_order(&mut self, roots: &[std::path::PathBuf]) {
        for root in roots {
            let Some(relative_root) = repository_relative_value(&self.repo_root, root) else {
                continue;
            };
            self.directory_order.push(relative_root.clone());
            let mut pending = vec![relative_root];
            while let Some(directory) = pending.pop() {
                let children = self
                    .direct_entries
                    .get(&directory)
                    .into_iter()
                    .flatten()
                    .filter(|path| self.directory_paths.contains(*path))
                    .cloned()
                    .collect::<Vec<_>>();
                self.directory_order.extend(children.iter().cloned());
                pending.extend(children.into_iter().rev());
            }
        }
        self.entries = self
            .directory_order
            .iter()
            .flat_map(|directory| self.direct_entries.get(directory).into_iter().flatten())
            .cloned()
            .collect();
    }

    fn python_anchor(&self, root: &str) -> Option<String> {
        let init = join_relative(root, "__init__.py");
        if self.file_paths.contains(&init) {
            return Some(init);
        }
        let mut direct = self
            .direct_entries
            .get(root)
            .into_iter()
            .flatten()
            .filter(|path| self.file_paths.contains(*path) && path.ends_with(".py"))
            .cloned()
            .collect::<Vec<_>>();
        direct.sort();
        if let Some(path) = direct.into_iter().next() {
            return Some(path);
        }
        let prefix = (root != REPOSITORY_ROOT_PATH).then(|| format!("{root}/"));
        let mut descendants = self
            .file_paths
            .iter()
            .filter(|path| {
                path.ends_with(".py")
                    && prefix
                        .as_ref()
                        .map(|prefix| path.starts_with(prefix))
                        .unwrap_or(true)
            })
            .cloned()
            .collect::<Vec<_>>();
        descendants.sort();
        descendants.into_iter().next()
    }
}

fn is_below(path: &str, root: &str) -> bool {
    path == root || relative_below(path, root).is_some()
}

fn relative_below<'a>(path: &'a str, root: &str) -> Option<&'a str> {
    if root == REPOSITORY_ROOT_PATH {
        return Some(path);
    }
    path.strip_prefix(root)?.strip_prefix('/')
}
