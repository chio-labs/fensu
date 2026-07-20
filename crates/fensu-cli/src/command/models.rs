use std::path::PathBuf;

use fensu_memory::engine::models::MemoryGraphQuery;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ColorMode {
    Auto,
    Always,
    Never,
}

#[derive(Debug)]
pub(crate) enum MemoryCommand {
    Summary,
    Archive {
        paths: Vec<PathBuf>,
        confirmed: bool,
    },
    Check,
    Sync,
    Rebuild,
    Schema {
        relation: Option<String>,
    },
    Graph {
        query: MemoryGraphQuery,
        format: String,
    },
    Sql {
        query: String,
        limit: usize,
        format: String,
    },
}

#[derive(Debug)]
pub(crate) struct ParsedMemory {
    pub(crate) command: MemoryCommand,
    pub(crate) color: ColorMode,
}

#[derive(Debug)]
pub(crate) struct MemoryProject {
    pub(crate) repository_root: PathBuf,
    pub(crate) database_path: PathBuf,
    pub(crate) archive_after_days: u64,
}
