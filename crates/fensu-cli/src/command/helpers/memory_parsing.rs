use std::path::PathBuf;

use fensu_memory::engine::models::{
    MemoryGraphDirection, MemoryGraphQuery, MemoryGraphRelationship,
};

use crate::command::constants::{
    DEFAULT_GRAPH_DEPTH, DEFAULT_GRAPH_EDGES, DEFAULT_GRAPH_NODES, DEFAULT_QUERY_LIMIT,
    MAX_QUERY_LIMIT, OPTION_TERMINATOR, QUERY_FORMAT_CSV, QUERY_FORMAT_JSON, QUERY_FORMAT_LONG,
    QUERY_FORMAT_TABLE,
};
use crate::command::models::{ColorMode, MemoryCommand, ParsedMemory};

pub(crate) fn parse(arguments: &[String]) -> Result<ParsedMemory, String> {
    let mut color = ColorMode::Auto;
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            OPTION_TERMINATOR => {
                let command = arguments.get(index + 1).ok_or_else(|| {
                    "fensu memory: error: the following arguments are required: command".to_owned()
                })?;
                let (command, color) = parse_command(command, &arguments[index + 2..], color)?;
                return Ok(ParsedMemory { command, color });
            }
            "--color" => {
                color = parse_color(option_value(arguments, index, "--color")?)?;
                index += 2;
            }
            command => {
                let (command, color) = parse_command(command, &arguments[index + 1..], color)?;
                return Ok(ParsedMemory { command, color });
            }
        }
    }
    Ok(ParsedMemory {
        command: MemoryCommand::Summary,
        color,
    })
}

pub(crate) fn normalize_options(arguments: &[String]) -> Vec<String> {
    let mut normalized = Vec::new();
    let mut options = true;
    for argument in arguments {
        if argument == OPTION_TERMINATOR {
            options = false;
        } else if options && argument.starts_with("--") {
            if let Some((name, value)) = argument.split_once('=') {
                normalized.extend([name.to_owned(), value.to_owned()]);
                continue;
            }
        }
        normalized.push(argument.clone());
    }
    normalized
}

fn parse_command(
    name: &str,
    arguments: &[String],
    color: ColorMode,
) -> Result<(MemoryCommand, ColorMode), String> {
    match name {
        "archive" => parse_archive(arguments, color),
        "check" => parse_empty(arguments, color, MemoryCommand::Check),
        "sync" => parse_empty(arguments, color, MemoryCommand::Sync),
        "rebuild" => parse_empty(arguments, color, MemoryCommand::Rebuild),
        "schema" => parse_schema(arguments, color),
        "graph" => parse_graph(arguments, color),
        "sql" => parse_sql(arguments, color),
        _ => Err(format!(
            "fensu memory: error: argument command: invalid choice: '{name}'"
        )),
    }
}

fn parse_empty(
    arguments: &[String],
    mut color: ColorMode,
    command: MemoryCommand,
) -> Result<(MemoryCommand, ColorMode), String> {
    let (arguments, trailing) = split_terminator(arguments);
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--color" => {
                color = parse_color(option_value(arguments, index, "--color")?)?;
                index += 2;
            }
            value => return Err(unrecognized(value)),
        }
    }
    if let Some(value) = trailing.first() {
        return Err(unrecognized(value));
    }
    Ok((command, color))
}

fn parse_archive(
    arguments: &[String],
    mut color: ColorMode,
) -> Result<(MemoryCommand, ColorMode), String> {
    let (arguments, trailing) = split_terminator(arguments);
    let mut paths = Vec::new();
    let mut confirmed = false;
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--yes" => confirmed = true,
            "--color" => {
                color = parse_color(option_value(arguments, index, "--color")?)?;
                index += 1;
            }
            value if value.starts_with('-') => return Err(unrecognized(value)),
            value => paths.push(PathBuf::from(value)),
        }
        index += 1;
    }
    paths.extend(trailing.iter().map(PathBuf::from));
    Ok((MemoryCommand::Archive { paths, confirmed }, color))
}

fn parse_schema(
    arguments: &[String],
    mut color: ColorMode,
) -> Result<(MemoryCommand, ColorMode), String> {
    let (arguments, trailing) = split_terminator(arguments);
    let mut relation = None;
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--color" => {
                color = parse_color(option_value(arguments, index, "--color")?)?;
                index += 1;
            }
            value if value.starts_with('-') => return Err(unrecognized(value)),
            value if relation.is_none() => relation = Some(value.to_owned()),
            value => return Err(unrecognized(value)),
        }
        index += 1;
    }
    if let Some(value) = trailing.first() {
        if relation.is_some() || trailing.len() > 1 {
            return Err(unrecognized(value));
        }
        relation = Some(value.to_owned());
    }
    Ok((MemoryCommand::Schema { relation }, color))
}

fn parse_graph(
    arguments: &[String],
    mut color: ColorMode,
) -> Result<(MemoryCommand, ColorMode), String> {
    let (arguments, trailing) = split_terminator(arguments);
    let mut pattern = None;
    let mut direction = MemoryGraphDirection::Outbound;
    let mut relationships = Vec::new();
    let mut depth = DEFAULT_GRAPH_DEPTH;
    let mut max_nodes = DEFAULT_GRAPH_NODES;
    let mut max_edges = DEFAULT_GRAPH_EDGES;
    let mut include_archived = false;
    let mut format = QUERY_FORMAT_LONG.to_owned();
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--direction" => {
                direction = parse_direction(option_value(arguments, index, "--direction")?)?;
                index += 1;
            }
            "--relationship" => {
                relationships.push(parse_relationship(option_value(
                    arguments,
                    index,
                    "--relationship",
                )?)?);
                index += 1;
            }
            "--depth" => {
                depth = bounded(option_value(arguments, index, "--depth")?, "depth", 1, 5)?;
                index += 1;
            }
            "--max-nodes" => {
                max_nodes = bounded(
                    option_value(arguments, index, "--max-nodes")?,
                    "max-nodes",
                    1,
                    200,
                )?;
                index += 1;
            }
            "--max-edges" => {
                max_edges = bounded(
                    option_value(arguments, index, "--max-edges")?,
                    "max-edges",
                    1,
                    500,
                )?;
                index += 1;
            }
            "--include-archived" => include_archived = true,
            "--format" => {
                format = choice(
                    option_value(arguments, index, "--format")?,
                    &[QUERY_FORMAT_LONG, QUERY_FORMAT_JSON],
                )?;
                index += 1;
            }
            "--color" => {
                color = parse_color(option_value(arguments, index, "--color")?)?;
                index += 1;
            }
            value if value.starts_with('-') => return Err(unrecognized(value)),
            value if pattern.is_none() => pattern = Some(value.to_owned()),
            value => return Err(unrecognized(value)),
        }
        index += 1;
    }
    if let Some(value) = trailing.first() {
        if pattern.is_some() || trailing.len() > 1 {
            return Err(unrecognized(value));
        }
        pattern = Some(value.to_owned());
    }
    let pattern = pattern.ok_or_else(|| {
        "fensu memory graph: error: the following arguments are required: DOCUMENT_OR_PATTERN"
            .to_owned()
    })?;
    Ok((
        MemoryCommand::Graph {
            query: MemoryGraphQuery {
                pattern,
                direction,
                relationships,
                depth,
                max_nodes,
                max_edges,
                include_archived,
            },
            format,
        },
        color,
    ))
}

fn parse_sql(
    arguments: &[String],
    mut color: ColorMode,
) -> Result<(MemoryCommand, ColorMode), String> {
    let (arguments, trailing) = split_terminator(arguments);
    let mut query = None;
    let mut limit = DEFAULT_QUERY_LIMIT;
    let mut limit_set = false;
    let mut no_limit = false;
    let mut format = QUERY_FORMAT_LONG.to_owned();
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--format" => {
                format = choice(
                    option_value(arguments, index, "--format")?,
                    &[
                        QUERY_FORMAT_LONG,
                        QUERY_FORMAT_TABLE,
                        QUERY_FORMAT_JSON,
                        QUERY_FORMAT_CSV,
                    ],
                )?;
                index += 1;
            }
            "--limit" => {
                if no_limit {
                    return Err("fensu memory sql: error: argument --limit: not allowed with argument --no-limit".to_owned());
                }
                limit = bounded(
                    option_value(arguments, index, "--limit")?,
                    "limit",
                    1,
                    MAX_QUERY_LIMIT,
                )?;
                limit_set = true;
                index += 1;
            }
            "--no-limit" => {
                if limit_set {
                    return Err("fensu memory sql: error: argument --no-limit: not allowed with argument --limit".to_owned());
                }
                no_limit = true;
                limit = MAX_QUERY_LIMIT;
            }
            "--color" => {
                color = parse_color(option_value(arguments, index, "--color")?)?;
                index += 1;
            }
            value if value.starts_with('-') => return Err(unrecognized(value)),
            value if query.is_none() => query = Some(value.to_owned()),
            value => return Err(unrecognized(value)),
        }
        index += 1;
    }
    if let Some(value) = trailing.first() {
        if query.is_some() || trailing.len() > 1 {
            return Err(unrecognized(value));
        }
        query = Some(value.to_owned());
    }
    let query = query.ok_or_else(|| {
        "fensu memory sql: error: the following arguments are required: QUERY".to_owned()
    })?;
    Ok((
        MemoryCommand::Sql {
            query,
            limit,
            format,
        },
        color,
    ))
}

fn option_value<'a>(arguments: &'a [String], index: usize, name: &str) -> Result<&'a str, String> {
    arguments
        .get(index + 1)
        .map(String::as_str)
        .ok_or_else(|| format!("fensu memory: error: argument {name}: expected one argument"))
}

fn split_terminator(arguments: &[String]) -> (&[String], &[String]) {
    arguments
        .iter()
        .position(|value| value == OPTION_TERMINATOR)
        .map_or((arguments, &[]), |index| {
            (&arguments[..index], &arguments[index + 1..])
        })
}

fn parse_color(value: &str) -> Result<ColorMode, String> {
    match value {
        "auto" => Ok(ColorMode::Auto),
        "always" => Ok(ColorMode::Always),
        "never" => Ok(ColorMode::Never),
        _ => Err(format!(
            "fensu memory: error: argument --color: invalid choice: '{value}'"
        )),
    }
}

fn parse_direction(value: &str) -> Result<MemoryGraphDirection, String> {
    match value {
        "outbound" => Ok(MemoryGraphDirection::Outbound),
        "inbound" => Ok(MemoryGraphDirection::Inbound),
        "both" => Ok(MemoryGraphDirection::Both),
        _ => Err(format!(
            "fensu memory graph: error: argument --direction: invalid choice: '{value}'"
        )),
    }
}

fn parse_relationship(value: &str) -> Result<MemoryGraphRelationship, String> {
    match value {
        "link" => Ok(MemoryGraphRelationship::Link),
        "related" => Ok(MemoryGraphRelationship::Related),
        "depends-on" => Ok(MemoryGraphRelationship::DependsOn),
        "supersedes" => Ok(MemoryGraphRelationship::Supersedes),
        "discovered-from" => Ok(MemoryGraphRelationship::DiscoveredFrom),
        "implements" => Ok(MemoryGraphRelationship::Implements),
        "documents" => Ok(MemoryGraphRelationship::Documents),
        _ => Err(format!(
            "fensu memory graph: error: argument --relationship: invalid choice: '{value}'"
        )),
    }
}

fn bounded(value: &str, name: &str, minimum: usize, maximum: usize) -> Result<usize, String> {
    let parsed = value.parse::<usize>().map_err(|_| {
        format!("fensu memory: error: argument --{name}: invalid integer value: '{value}'")
    })?;
    if (minimum..=maximum).contains(&parsed) {
        Ok(parsed)
    } else {
        Err(format!(
            "fensu memory: error: argument --{name}: {name} must be between {minimum} and {maximum}"
        ))
    }
}

fn choice(value: &str, choices: &[&str]) -> Result<String, String> {
    if choices.contains(&value) {
        Ok(value.to_owned())
    } else {
        Err(format!(
            "fensu memory: error: invalid choice: '{value}' (choose from {})",
            choices.join(", ")
        ))
    }
}

fn unrecognized(value: &str) -> String {
    format!("fensu memory: error: unrecognized arguments: {value}")
}
