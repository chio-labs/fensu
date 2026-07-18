//! Generated fixtures for bounded streaming tests.

use std::fs;
use std::path::Path;

pub(crate) fn write_cross_chunk_cycle(root: &Path, document_count: usize) {
    let parent = root.join(".ai/tasks/not-started");
    fs::create_dir_all(&parent).expect("streaming task parent is writable");
    for index in 0..document_count {
        let name = format!("20260718T140000_{index:06}Z__FEAT-streaming-{index}.md");
        fs::write(parent.join(name), format!("# Streaming Task {index}\n"))
            .expect("streaming task is writable");
    }
    let last = document_count - 1;
    let first_name = "20260718T140000_000000Z__FEAT-streaming-0.md";
    let last_name = format!("20260718T140000_{last:06}Z__FEAT-streaming-{last}.md");
    fs::write(
        parent.join(first_name),
        format!("# Streaming Task 0\n\n- depends-on: [[{last_name}]]\n"),
    )
    .expect("first streaming task is writable");
    fs::write(
        parent.join(&last_name),
        format!("# Streaming Task {last}\n\n- depends-on: [[{first_name}]]\n"),
    )
    .expect("last streaming task is writable");
}

pub(crate) fn write_late_invalid_documents(root: &Path, document_count: usize) {
    let parent = root.join(".ai/knowledge/repo/notes");
    for index in 1..document_count - 1 {
        let name = format!("20260718T150000_{index:06}Z__NOTE-streaming-{index}.md");
        fs::write(parent.join(name), format!("# Streaming Note {index}\n"))
            .expect("streaming note is writable");
    }
    let invalid = parent.join("20260718T150000_999999Z__NOTE-streaming-invalid.md");
    fs::write(invalid, "missing title\n").expect("late invalid note is writable");
}

pub(crate) fn write_late_identity_collision(root: &Path, document_count: usize) {
    let archived = root.join(".ai/_archive/knowledge/repo/notes");
    let active = root.join(".ai/knowledge/repo/notes");
    fs::create_dir_all(&archived).expect("archived streaming parent is writable");
    for index in 0..document_count - 1 {
        let name = format!("20260718T160000_{index:06}Z__NOTE-collision-{index}.md");
        fs::write(archived.join(name), format!("# Collision {index}\n"))
            .expect("archived collision note is writable");
    }
    let duplicate = "20260718T160000_000000Z__NOTE-collision-active.md";
    fs::write(active.join(duplicate), "# Active Collision\n")
        .expect("active collision note is writable");
}
