//! Temporary repository and result helpers for corpus tests.

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

use crate::test_types::FixtureFile;
use fensu_memory::corpus::models::MemoryCorpus;
use fensu_memory::corpus::types::CorpusDiagnosticKind;

static TREE_COUNTER: AtomicUsize = AtomicUsize::new(0);

pub(crate) fn write_temp_tree(files: &[FixtureFile]) -> PathBuf {
    let index = TREE_COUNTER.fetch_add(1, Ordering::SeqCst);
    let root = std::env::temp_dir().join(format!(
        "fensu-memory-corpus-{}-{index}",
        std::process::id()
    ));
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(&root).expect("temporary repository root is writable");
    for file in files {
        let path = root.join(file.path);
        fs::create_dir_all(path.parent().expect("fixture file has a parent"))
            .expect("fixture parent is writable");
        fs::write(path, file.contents).expect("fixture file is writable");
    }
    root
}

pub(crate) fn document_paths(corpus: &MemoryCorpus) -> Vec<&str> {
    corpus
        .documents
        .iter()
        .map(|document| document.source.canonical_path.repository_relative.as_str())
        .collect()
}

pub(crate) fn parsed_titles(corpus: &MemoryCorpus) -> Vec<Option<&str>> {
    corpus
        .documents
        .iter()
        .map(|document| {
            document
                .parsed_markdown
                .as_ref()
                .and_then(|parsed| parsed.title.as_deref())
        })
        .collect()
}

pub(crate) fn diagnostic_rows(corpus: &MemoryCorpus) -> Vec<(&str, CorpusDiagnosticKind)> {
    corpus
        .diagnostics
        .iter()
        .map(|diagnostic| {
            (
                diagnostic.repository_relative_path.as_str(),
                diagnostic.kind,
            )
        })
        .collect()
}

pub(crate) fn source_diagnostic_paths(corpus: &MemoryCorpus) -> Vec<&str> {
    corpus
        .source_diagnostics
        .iter()
        .map(|diagnostic| diagnostic.repository_relative_path.as_str())
        .collect()
}

pub(crate) fn skill_file_paths(corpus: &MemoryCorpus) -> Vec<&str> {
    corpus
        .skill_files
        .iter()
        .map(|file| file.canonical_path.repository_relative.as_str())
        .collect()
}

pub(crate) fn remove_temp_tree(root: &Path) {
    fs::remove_dir_all(root).expect("temporary repository is removable");
}
