use std::fmt::Write;
use std::path::Path;

use fensu_memory::engine::models::{
    IndexSummary, MemoryArchiveResult, MemoryOverview, MemoryQueryResult, MemorySchemaColumn,
    MemorySchemaOverview, MemorySchemaRelation, SyncSummary,
};

use crate::command::constants::{RELATION_KIND_TABLE, RELATION_KIND_VIEW};
use crate::command::helpers::memory_values::{heading, query_value};

pub(crate) fn sync(
    summary: &SyncSummary,
    repository_root: &Path,
    database_path: &Path,
    compact: bool,
    color: bool,
) -> String {
    if compact {
        if !summary.changed {
            return String::new();
        }
        return format!(
            "{}: +{} ~{} >{} -{}\n",
            heading("Memory synced", color),
            summary.added_count,
            summary.changed_count,
            summary.moved_count,
            summary.removed_count
        );
    }
    let rebuilt = if summary.rebuilt { "yes" } else { "no" };
    format!(
        "{}: added={} changed={} moved={} removed={} unchanged={} rebuilt={rebuilt}\n{}: documents={} sections={} links={}\n{}: {}\n{}: {}\n",
        heading("Memory sync", color),
        summary.added_count,
        summary.changed_count,
        summary.moved_count,
        summary.removed_count,
        summary.unchanged_count,
        heading("Index", color),
        summary.document_count,
        summary.section_count,
        summary.link_count,
        heading("Repository", color),
        repository_root.display(),
        heading("Database", color),
        database_path.display(),
    )
}

pub(crate) fn overview(overview: &MemoryOverview, color: bool) -> String {
    format!(
        "{}: {} not started, {} in progress, {} completed, {} cancelled, {} superseded\n{}: {} notes, {} decisions, {} skills\n{}: {} tasks, {} knowledge\n{}: {} documents, {} sections\nSQL: fensu memory sql \"SELECT * FROM memory.current_tasks\"\n",
        heading("Tasks", color),
        overview.not_started_task_count,
        overview.in_progress_task_count,
        overview.completed_task_count,
        overview.cancelled_task_count,
        overview.superseded_task_count,
        heading("Knowledge", color),
        overview.active_note_count,
        overview.active_decision_count,
        overview.active_skill_count,
        heading("Archive", color),
        overview.archived_task_count,
        overview.archived_knowledge_count,
        heading("Index", color),
        overview.document_count,
        overview.section_count,
    )
}

pub(crate) fn rebuild(
    summary: &IndexSummary,
    repository_root: &Path,
    database_path: &Path,
    color: bool,
) -> String {
    format!(
        "{}: documents={} sections={} list_items={} links={} tags={} skill_files={}\n{}: source={} corpus={} graph={}\n{}: {}\n{}: {}\n",
        heading("Memory rebuilt", color),
        summary.document_count,
        summary.section_count,
        summary.list_item_count,
        summary.link_count,
        summary.tag_count,
        summary.skill_file_count,
        heading("Diagnostics", color),
        summary.source_diagnostic_count,
        summary.corpus_diagnostic_count,
        summary.graph_diagnostic_count,
        heading("Repository", color),
        repository_root.display(),
        heading("Database", color),
        database_path.display(),
    )
}

pub(crate) fn schema(schema: &MemorySchemaOverview, color: bool) -> String {
    let tables = schema
        .relations
        .iter()
        .filter(|relation| relation.kind == RELATION_KIND_TABLE)
        .copied()
        .collect::<Vec<_>>();
    let views = schema
        .relations
        .iter()
        .filter(|relation| relation.kind == RELATION_KIND_VIEW)
        .copied()
        .collect::<Vec<_>>();
    format!(
        "Memory schema {} (parser contract {})\n\n{}:\n{}\n\n{}:\n{}\n",
        schema.schema_version,
        schema.parser_contract_version,
        heading("Stored tables", color),
        relation_lines(&tables),
        heading("Convenience views", color),
        relation_lines(&views),
    )
}

pub(crate) fn relation(relation: &MemorySchemaRelation, color: bool) -> String {
    format!(
        "{} ({})\n{}\n\n{}\n",
        heading(relation.name, color),
        relation.kind,
        relation.comment,
        column_lines(relation.columns),
    )
}

pub(crate) fn archive(result: &MemoryArchiveResult, color: bool) -> String {
    if result.moves.is_empty() {
        return format!(
            "{}: no eligible sources\n",
            heading("Memory archive", color)
        );
    }
    let mut output = format!("{}:\n", heading("Memory archived", color));
    for entry in &result.moves {
        let _ = writeln!(output, "  {} -> {}", entry.source, entry.destination);
    }
    if let Some(sync) = &result.sync {
        let _ = writeln!(
            output,
            "Index: documents={} sections={} links={}",
            sync.document_count, sync.section_count, sync.link_count
        );
    }
    output
}

pub(crate) fn query_long(result: &MemoryQueryResult, color: bool) -> String {
    let width = result
        .columns
        .iter()
        .map(|column| column.chars().count())
        .max()
        .unwrap_or(0);
    let mut lines = Vec::new();
    for (index, row) in result.rows.iter().enumerate() {
        lines.push(heading(&format!("-[ RECORD {} ]-", index + 1), color));
        for (column, value) in result.columns.iter().zip(row) {
            lines.push(format!(
                "{column:<width$} | {}",
                query_value(value),
                width = width
            ));
        }
    }
    lines.push(query_count(result));
    format!("{}\n", lines.join("\n"))
}

pub(crate) fn query_table(result: &MemoryQueryResult, color: bool) -> String {
    let rendered_rows = result
        .rows
        .iter()
        .map(|row| row.iter().map(query_value).collect::<Vec<_>>())
        .collect::<Vec<_>>();
    let mut widths = result
        .columns
        .iter()
        .map(|column| column.chars().count())
        .collect::<Vec<_>>();
    for row in &rendered_rows {
        for (index, value) in row.iter().enumerate() {
            widths[index] = widths[index].max(value.chars().count());
        }
    }
    let header = result
        .columns
        .iter()
        .enumerate()
        .map(|(index, column)| format!("{column:<width$}", width = widths[index]))
        .collect::<Vec<_>>()
        .join(" | ");
    let mut lines = vec![heading(&header, color)];
    lines.push(
        widths
            .iter()
            .map(|width| "-".repeat(*width))
            .collect::<Vec<_>>()
            .join("-+-"),
    );
    for row in rendered_rows {
        lines.push(
            row.iter()
                .enumerate()
                .map(|(index, value)| format!("{value:<width$}", width = widths[index]))
                .collect::<Vec<_>>()
                .join(" | ")
                .trim_end()
                .to_owned(),
        );
    }
    lines.push(query_count(result));
    format!("{}\n", lines.join("\n"))
}

fn relation_lines(relations: &[MemorySchemaRelation]) -> String {
    if relations.is_empty() {
        return "  (none)".to_owned();
    }
    let width = relations
        .iter()
        .map(|relation| relation.name.chars().count())
        .max()
        .unwrap_or(0);
    relations
        .iter()
        .map(|relation| {
            format!(
                "  {:width$}  {}",
                relation.name,
                relation.comment,
                width = width
            )
        })
        .collect::<Vec<_>>()
        .join("\n")
}

fn column_lines(columns: &[MemorySchemaColumn]) -> String {
    let headings = ["Column", "Type", "Nullable", "Meaning"];
    let rows = columns
        .iter()
        .map(|column| {
            [
                column.name,
                column.data_type,
                if column.nullable { "yes" } else { "no" },
                column.comment,
            ]
        })
        .collect::<Vec<_>>();
    let mut widths = headings.map(str::len);
    for row in &rows {
        for (index, value) in row.iter().enumerate() {
            widths[index] = widths[index].max(value.chars().count());
        }
    }
    let mut lines = vec![render_cells(&headings, &widths)];
    lines.push(
        widths
            .iter()
            .map(|width| "-".repeat(*width))
            .collect::<Vec<_>>()
            .join("-+-"),
    );
    lines.extend(rows.iter().map(|row| render_cells(row, &widths)));
    lines.join("\n")
}

fn render_cells(values: &[&str; 4], widths: &[usize; 4]) -> String {
    values
        .iter()
        .enumerate()
        .map(|(index, value)| format!("{value:<width$}", width = widths[index]))
        .collect::<Vec<_>>()
        .join(" | ")
        .trim_end()
        .to_owned()
}

fn query_count(result: &MemoryQueryResult) -> String {
    let noun = if result.rows.len() == 1 {
        "row"
    } else {
        "rows"
    };
    let suffix = if result.truncated { ", truncated" } else { "" };
    format!("({} {noun}{suffix})", result.rows.len())
}
