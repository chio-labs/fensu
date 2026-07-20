use fensu_memory::engine::models::{MemoryGraphQuery, MemoryGraphResult, MemoryQueryResult};

use crate::command::helpers::memory_values::{
    direction_name, json_string, json_value, query_value,
};

pub(crate) fn query_csv(result: &MemoryQueryResult) -> String {
    let mut output = result
        .columns
        .iter()
        .map(|value| csv_field(value))
        .collect::<Vec<_>>()
        .join(",");
    output.push_str("\r\n");
    for row in &result.rows {
        output.push_str(
            &row.iter()
                .map(query_value)
                .map(|value| csv_field(&value))
                .collect::<Vec<_>>()
                .join(","),
        );
        output.push_str("\r\n");
    }
    output
}

pub(crate) fn query_json(result: &MemoryQueryResult) -> String {
    let columns = result
        .columns
        .iter()
        .map(|value| json_string(value, false))
        .collect::<Vec<_>>()
        .join(",");
    let types = result
        .types
        .iter()
        .map(|value| json_string(value, false))
        .collect::<Vec<_>>()
        .join(",");
    let rows = result
        .rows
        .iter()
        .map(|row| {
            format!(
                "[{}]",
                row.iter()
                    .map(|value| json_value(value, false, false))
                    .collect::<Vec<_>>()
                    .join(",")
            )
        })
        .collect::<Vec<_>>()
        .join(",");
    format!(
        "{{\"columns\":[{columns}],\"types\":[{types}],\"rows\":[{rows}],\"truncated\":{}}}\n",
        result.truncated
    )
}

pub(crate) fn graph_json(result: &MemoryGraphResult, query: &MemoryGraphQuery) -> String {
    let edges = result
        .edges
        .iter()
        .map(|edge| {
            format!(
                "{{\"authored_target\":{},\"cycle\":{},\"relationship\":{},\"resolution_status\":{},\"source_document_identity\":{},\"source_link_ordinal\":{},\"target_document_identity\":{}}}",
                json_string(&edge.authored_target, true),
                edge.cycle,
                json_string(&edge.relationship, true),
                json_string(&edge.resolution_status, true),
                json_string(&edge.source_document_identity, true),
                edge.source_link_ordinal,
                edge.target_document_identity.as_ref().map_or_else(|| "null".to_owned(), |value| json_string(value, true)),
            )
        })
        .collect::<Vec<_>>()
        .join(",");
    let nodes = result
        .nodes
        .iter()
        .map(|node| {
            format!(
                "{{\"archive_state\":{},\"artifact_kind\":{},\"basename\":{},\"depth\":{},\"identity\":{},\"repository_relative_path\":{},\"root\":{},\"slug\":{},\"title\":{}}}",
                json_string(&node.archive_state, true),
                json_string(&node.artifact_kind, true),
                json_string(&node.basename, true),
                node.depth,
                json_string(&node.identity, true),
                json_string(&node.repository_relative_path, true),
                node.root,
                json_string(&node.slug, true),
                node.title.as_ref().map_or_else(|| "null".to_owned(), |value| json_string(value, true)),
            )
        })
        .collect::<Vec<_>>()
        .join(",");
    let relationships = query
        .relationships
        .iter()
        .map(|value| json_string(value.as_str(), true))
        .collect::<Vec<_>>()
        .join(",");
    let roots = result
        .roots
        .iter()
        .map(|value| json_string(value, true))
        .collect::<Vec<_>>()
        .join(",");
    format!(
        "{{\"depth\":{},\"direction\":{},\"edges\":[{edges}],\"include_archived\":{},\"limits\":{{\"max_edges\":{},\"max_nodes\":{}}},\"nodes\":[{nodes}],\"pattern\":{},\"relationships\":[{relationships}],\"roots\":[{roots}],\"selection\":{},\"truncated\":{{\"edges\":{},\"nodes\":{}}}}}\n",
        query.depth,
        json_string(direction_name(query.direction), true),
        query.include_archived,
        query.max_edges,
        query.max_nodes,
        json_string(&query.pattern, true),
        json_string(&result.selection, true),
        result.edge_budget_exhausted,
        result.node_budget_exhausted,
    )
}

fn csv_field(value: &str) -> String {
    if value.contains([',', '"', '\r', '\n']) {
        format!("\"{}\"", value.replace('"', "\"\""))
    } else {
        value.to_owned()
    }
}
