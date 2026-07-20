use std::env;
use std::io::{self, IsTerminal};
use std::path::Path;

use fensu_memory::engine::main::archive_memory::archive_memory;
use fensu_memory::engine::main::check_memory::check_memory;
use fensu_memory::engine::main::memory_overview::memory_overview;
use fensu_memory::engine::main::memory_relation_schema::memory_relation_schema;
use fensu_memory::engine::main::memory_schema::memory_schema;
use fensu_memory::engine::main::query_memory_graph::query_memory_graph;
use fensu_memory::engine::main::query_memory_index::query_memory_index;
use fensu_memory::engine::main::rebuild_memory_index::rebuild_memory_index;
use fensu_memory::engine::main::sync_memory_index::sync_memory_index;
use fensu_memory::engine::models::{MemoryGraphQuery, MemoryQueryResult, SyncSummary};
use fensu_memory::source::main::bootstrap_memory::bootstrap_memory;

use crate::command::constants::{
    MEMORY_SCHEMA_PREFIX, QUERY_FORMAT_CSV, QUERY_FORMAT_JSON, QUERY_FORMAT_TABLE,
};
use crate::command::helpers::{
    memory_graph_rendering, memory_help, memory_human_rendering, memory_parsing,
    memory_structured_rendering,
};
use crate::command::models::{ColorMode, MemoryCommand, MemoryProject};
use crate::configuration::main::load;
use crate::helpers::render;
use crate::models::{CliOutput, Fault};

pub(crate) fn execute_memory(arguments: &[String]) -> Result<CliOutput, String> {
    let arguments = memory_parsing::normalize_options(arguments);
    if memory_help::requested(&arguments) {
        return Ok(CliOutput::success(memory_help::text(&arguments)));
    }
    let parsed = memory_parsing::parse(&arguments)?;
    let color = use_color(parsed.color);
    let project = resolve_project()?;
    execute(parsed.command, &project, color)
}

fn execute(
    command: MemoryCommand,
    project: &MemoryProject,
    color: bool,
) -> Result<CliOutput, String> {
    match command {
        MemoryCommand::Summary => summarize(project, color),
        MemoryCommand::Archive { paths, confirmed } => {
            let result = archive_memory(
                &project.repository_root,
                &project.database_path,
                &paths,
                project.archive_after_days,
                confirmed,
            )
            .map_err(|error| format!("Memory archive failed: {error}"))?;
            Ok(CliOutput::success(memory_human_rendering::archive(
                &result, color,
            )))
        }
        MemoryCommand::Check => check(project, color),
        MemoryCommand::Sync => {
            let summary = sync(project)?;
            Ok(CliOutput::success(memory_human_rendering::sync(
                &summary,
                &project.repository_root,
                &project.database_path,
                false,
                color,
            )))
        }
        MemoryCommand::Rebuild => {
            let summary = rebuild_memory_index(&project.repository_root, &project.database_path)
                .map_err(|error| format!("Memory rebuild failed: {error}"))?;
            Ok(CliOutput::success(memory_human_rendering::rebuild(
                &summary,
                &project.repository_root,
                &project.database_path,
                color,
            )))
        }
        MemoryCommand::Schema { relation } => schema(relation.as_deref(), color),
        MemoryCommand::Graph { query, format } => graph(project, &query, &format, color),
        MemoryCommand::Sql {
            query,
            limit,
            format,
        } => sql(project, &query, limit, &format, color),
    }
}

fn summarize(project: &MemoryProject, color: bool) -> Result<CliOutput, String> {
    let summary = sync(project)?;
    let overview = memory_overview(&project.database_path)
        .map_err(|error| format!("Memory overview failed: {error}"))?;
    let mut output = memory_human_rendering::sync(
        &summary,
        &project.repository_root,
        &project.database_path,
        true,
        color,
    );
    output.push_str(&memory_human_rendering::overview(&overview, color));
    Ok(CliOutput::success(output))
}

fn check(project: &MemoryProject, color: bool) -> Result<CliOutput, String> {
    let result = check_memory(&project.repository_root, &project.database_path)
        .map_err(|error| format!("Memory check failed: {error}"))?;
    let faults = result
        .diagnostics
        .iter()
        .map(|diagnostic| Fault {
            code: diagnostic.code.to_owned(),
            path: project
                .repository_root
                .join(&diagnostic.repository_relative_path)
                .to_string_lossy()
                .into_owned(),
            line: diagnostic.line.and_then(|value| u32::try_from(value).ok()),
            column: diagnostic
                .column
                .and_then(|value| u32::try_from(value).ok()),
            message: diagnostic.message.clone(),
            remediation: Some(diagnostic.remediation.to_owned()),
            warning: false,
        })
        .collect::<Vec<_>>();
    let stdout = render::report(render::ReportRequest {
        faults: &faults,
        warnings: &[],
        root: &project.repository_root,
        color,
        show_warnings: false,
        evaluation_summary: None,
        applied_exceptions: 0,
        threshold_uses: &[],
    });
    Ok(CliOutput {
        stdout,
        stderr: String::new(),
        exit_code: i32::from(!faults.is_empty()),
    })
}

fn schema(relation: Option<&str>, color: bool) -> Result<CliOutput, String> {
    if let Some(name) = relation {
        let qualified = if name.starts_with(MEMORY_SCHEMA_PREFIX) {
            name.to_owned()
        } else {
            format!("{MEMORY_SCHEMA_PREFIX}{name}")
        };
        let relation = memory_relation_schema(&qualified)
            .ok_or_else(|| format!("Unknown memory relation: {qualified}"))?;
        return Ok(CliOutput::success(memory_human_rendering::relation(
            &relation, color,
        )));
    }
    Ok(CliOutput::success(memory_human_rendering::schema(
        &memory_schema(),
        color,
    )))
}

fn graph(
    project: &MemoryProject,
    query: &MemoryGraphQuery,
    format: &str,
    color: bool,
) -> Result<CliOutput, String> {
    let summary = sync(project)?;
    let result = query_memory_graph(&project.database_path, query)
        .map_err(|error| format!("Memory graph failed: {error}"))?;
    let machine = format == QUERY_FORMAT_JSON;
    let stdout = if machine {
        memory_structured_rendering::graph_json(&result, query)
    } else {
        memory_graph_rendering::graph(&result, query, color)
    };
    Ok(CliOutput {
        stdout,
        stderr: memory_human_rendering::sync(
            &summary,
            &project.repository_root,
            &project.database_path,
            true,
            color && !machine,
        ),
        exit_code: 0,
    })
}

fn sql(
    project: &MemoryProject,
    query: &str,
    limit: usize,
    format: &str,
    color: bool,
) -> Result<CliOutput, String> {
    let summary = sync(project)?;
    let result = query_memory_index(&project.database_path, query, limit)
        .map_err(|error| format!("Memory query failed: {error}"))?;
    let human = format != QUERY_FORMAT_JSON && format != QUERY_FORMAT_CSV;
    Ok(CliOutput {
        stdout: render_query(&result, format, color && human),
        stderr: memory_human_rendering::sync(
            &summary,
            &project.repository_root,
            &project.database_path,
            true,
            color && human,
        ),
        exit_code: 0,
    })
}

fn render_query(result: &MemoryQueryResult, format: &str, color: bool) -> String {
    match format {
        QUERY_FORMAT_JSON => memory_structured_rendering::query_json(result),
        QUERY_FORMAT_CSV => memory_structured_rendering::query_csv(result),
        QUERY_FORMAT_TABLE => memory_human_rendering::query_table(result, color),
        _ => memory_human_rendering::query_long(result, color),
    }
}

fn sync(project: &MemoryProject) -> Result<SyncSummary, String> {
    sync_memory_index(&project.repository_root, &project.database_path)
        .map_err(|error| format!("Memory sync failed: {error}"))
}

fn resolve_project() -> Result<MemoryProject, String> {
    let (source_path, loaded) = load::load(Path::new("."))?;
    let repository_root = source_path
        .parent()
        .ok_or_else(|| "Fensu configuration has no repository directory.".to_owned())?
        .to_path_buf();
    if !loaded.memory_enabled {
        return Err(
            "Fensu Memory is disabled; set experimental.memory = true in the project configuration."
                .to_owned(),
        );
    }
    bootstrap_memory(&repository_root)?;
    let database_path = repository_root.join(".fensu/memory/memory.sqlite3");
    Ok(MemoryProject {
        repository_root,
        database_path,
        archive_after_days: loaded.memory_archive_after_days,
    })
}

fn use_color(mode: ColorMode) -> bool {
    env::var_os("NO_COLOR").is_none()
        && (mode == ColorMode::Always || mode == ColorMode::Auto && io::stdout().is_terminal())
}
