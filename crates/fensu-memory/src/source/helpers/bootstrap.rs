use std::fs::{self, File, OpenOptions};
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};

#[cfg(unix)]
use std::os::unix::fs::OpenOptionsExt;

use crate::engine::main::summarize_memory::summarize_memory;

const DATABASE_DIRECTORY: &str = ".fensu/memory";
const BOOTSTRAP_FILE: &str = ".bootstrapped";
const GITIGNORE_FILE: &str = ".gitignore";
const GITIGNORE_ENTRY: &str = ".fensu/memory/";
const GITIGNORE_BLOCK: &[u8] = b"# Fensu\n.fensu/memory/\n";
const MEMORY_DIRECTORIES: &[&str] = &[
    ".ai/tasks/not-started",
    ".ai/tasks/in-progress",
    ".ai/tasks/completed",
    ".ai/tasks/cancelled",
    ".ai/tasks/superseded",
    ".ai/knowledge/repo/notes",
    ".ai/knowledge/repo/decisions",
    ".ai/knowledge/repo/skills",
    ".ai/_archive/tasks/completed",
    ".ai/_archive/tasks/cancelled",
    ".ai/_archive/tasks/superseded",
    ".ai/_archive/knowledge/repo/notes",
    ".ai/_archive/knowledge/repo/decisions",
    ".ai/_archive/knowledge/repo/skills",
];

pub(crate) fn bootstrap(repository_root: &Path) -> Result<(), String> {
    let marker_path = repository_root
        .join(DATABASE_DIRECTORY)
        .join(BOOTSTRAP_FILE);
    if marker_path.is_file() && has_complete_structure(repository_root) {
        ensure_gitignore(repository_root)?;
        return Ok(());
    }
    let summary = summarize_memory(repository_root);
    let diagnostic_count = summary.source_diagnostic_count
        + summary.corpus_diagnostic_count
        + summary.graph_diagnostic_count;
    if diagnostic_count > 0 {
        return Err(
            "Existing .ai content is not canonical and will not be migrated automatically; migrate it manually before using memory."
                .to_owned(),
        );
    }
    ensure_gitignore(repository_root)?;
    for relative_path in MEMORY_DIRECTORIES {
        let path = repository_root.join(relative_path);
        fs::create_dir_all(&path).map_err(|error| {
            format!(
                "Memory bootstrap could not create directory {}: {error}",
                path.display()
            )
        })?;
    }
    let parent = marker_path
        .parent()
        .ok_or_else(|| "Memory bootstrap marker has no parent directory.".to_owned())?;
    fs::create_dir_all(parent).map_err(|error| {
        format!(
            "Memory bootstrap could not create directory {}: {error}",
            parent.display()
        )
    })?;
    OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(false)
        .open(&marker_path)
        .map_err(|error| {
            format!(
                "Memory bootstrap could not create {}: {error}",
                marker_path.display()
            )
        })?;
    Ok(())
}

fn has_complete_structure(repository_root: &Path) -> bool {
    MEMORY_DIRECTORIES
        .iter()
        .all(|relative_path| repository_root.join(relative_path).is_dir())
}

fn ensure_gitignore(repository_root: &Path) -> Result<(), String> {
    let path = repository_root.join(GITIGNORE_FILE);
    match open_existing_gitignore(&path) {
        Ok(mut file) => update_gitignore(&mut file, &path),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => create_gitignore(&path),
        Err(error) => Err(format!(
            "Memory bootstrap could not open {}: {error}",
            path.display()
        )),
    }
}

fn open_existing_gitignore(path: &Path) -> std::io::Result<File> {
    let mut options = OpenOptions::new();
    options.read(true).write(true).append(true);
    #[cfg(unix)]
    options.custom_flags(libc::O_NOFOLLOW);
    options.open(path)
}

fn update_gitignore(file: &mut File, path: &Path) -> Result<(), String> {
    let metadata = file.metadata().map_err(|error| {
        format!(
            "Memory bootstrap could not inspect {}: {error}",
            path.display()
        )
    })?;
    if !metadata.is_file() {
        return Err(format!(
            "Memory bootstrap requires a regular root gitignore: {}",
            path.display()
        ));
    }
    file.seek(SeekFrom::Start(0)).map_err(|error| {
        format!(
            "Memory bootstrap could not update {}: {error}",
            path.display()
        )
    })?;
    let mut content = Vec::new();
    file.read_to_end(&mut content).map_err(|error| {
        format!(
            "Memory bootstrap could not update {}: {error}",
            path.display()
        )
    })?;
    if content.split(|byte| *byte == b'\n').any(|line| {
        line.strip_suffix(b"\r") == Some(GITIGNORE_ENTRY.as_bytes())
            || line == GITIGNORE_ENTRY.as_bytes()
    }) {
        return Ok(());
    }
    if !content.is_empty() && !content.ends_with(b"\n") {
        file.write_all(b"\n")
            .map_err(|error| gitignore_write_error(path, error))?;
    }
    file.write_all(GITIGNORE_BLOCK)
        .map_err(|error| gitignore_write_error(path, error))?;
    file.sync_all()
        .map_err(|error| gitignore_write_error(path, error))?;
    Ok(())
}

fn create_gitignore(path: &Path) -> Result<(), String> {
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        options.mode(0o644).custom_flags(libc::O_NOFOLLOW);
    }
    let mut file = options.open(path).map_err(|error| {
        format!(
            "Memory bootstrap could not create {}: {error}",
            path.display()
        )
    })?;
    file.write_all(GITIGNORE_BLOCK)
        .map_err(|error| gitignore_write_error(path, error))?;
    file.sync_all()
        .map_err(|error| gitignore_write_error(path, error))?;
    Ok(())
}

fn gitignore_write_error(path: &Path, error: std::io::Error) -> String {
    format!(
        "Memory bootstrap could not write {}: {error}",
        PathBuf::from(path).display()
    )
}
