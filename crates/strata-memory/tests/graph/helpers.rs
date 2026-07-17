//! Temporary repository and graph observation helpers.

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

use crate::test_types::FixtureFile;
use strata_memory::corpus::main::load_memory_corpus::load_memory_corpus;
use strata_memory::graph::main::resolve_memory_graph::resolve_memory_graph;
use strata_memory::graph::models::MemoryGraph;

static TREE_COUNTER: AtomicUsize = AtomicUsize::new(0);

pub(crate) fn load_graph(files: &[FixtureFile]) -> (PathBuf, MemoryGraph) {
    let index = TREE_COUNTER.fetch_add(1, Ordering::SeqCst);
    let root = std::env::temp_dir().join(format!(
        "strata-memory-graph-{}-{index}",
        std::process::id()
    ));
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(&root).expect("temporary graph repository root is writable");
    for file in files {
        let path = root.join(file.path);
        fs::create_dir_all(path.parent().expect("graph fixture file has a parent"))
            .expect("graph fixture parent is writable");
        fs::write(path, file.contents).expect("graph fixture file is writable");
    }
    let corpus = load_memory_corpus(&root);
    (root, resolve_memory_graph(&corpus))
}

pub(crate) fn remove_temp_tree(root: &Path) {
    fs::remove_dir_all(root).expect("temporary graph repository is removable");
}
