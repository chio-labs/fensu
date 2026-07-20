use std::collections::HashMap;

use fensu_memory::engine::models::{MemoryGraphNode, MemoryGraphQuery, MemoryGraphResult};

use crate::command::constants::{ARCHIVE_STATE_ARCHIVED, RESOLUTION_STATUS_RESOLVED};
use crate::command::helpers::memory_values::{direction_name, heading};

pub(crate) fn graph(result: &MemoryGraphResult, query: &MemoryGraphQuery, color: bool) -> String {
    let nodes = result
        .nodes
        .iter()
        .map(|node| (node.identity.as_str(), node))
        .collect::<HashMap<_, _>>();
    let mut lines = vec![
        heading("Memory graph", color),
        format!(
            "Selection: {} ({} root(s)), {}, depth {}",
            result.selection,
            result.roots.len(),
            direction_name(query.direction),
            query.depth
        ),
        String::new(),
        format!("Nodes ({}):", result.nodes.len()),
    ];
    for node in &result.nodes {
        let marker = if node.root {
            "root".to_owned()
        } else {
            format!("depth {}", node.depth)
        };
        let archived = if node.archive_state == ARCHIVE_STATE_ARCHIVED {
            ", archived"
        } else {
            ""
        };
        lines.push(format!(
            "  [{marker}{archived}] {} ({}) <{}> {}",
            node.title.as_deref().unwrap_or(&node.basename),
            node.artifact_kind,
            node.identity,
            node.repository_relative_path
        ));
    }
    lines.extend([String::new(), format!("Edges ({}):", result.edges.len())]);
    for edge in &result.edges {
        let source = node_label(&edge.source_document_identity, &nodes);
        let target = if edge.resolution_status == RESOLUTION_STATUS_RESOLVED {
            edge.target_document_identity
                .as_deref()
                .map(|identity| node_label(identity, &nodes))
                .unwrap_or_else(|| edge.authored_target.clone())
        } else {
            edge.authored_target.clone()
        };
        let mut labels = vec![edge.resolution_status.as_str()];
        if edge
            .target_document_identity
            .as_deref()
            .and_then(|identity| nodes.get(identity))
            .is_some_and(|node| node.archive_state == ARCHIVE_STATE_ARCHIVED)
        {
            labels.push(ARCHIVE_STATE_ARCHIVED);
        }
        if edge.cycle {
            labels.push("cycle");
        }
        lines.push(format!(
            "  {source} --{}--> {target} [{}]",
            edge.relationship,
            labels.join(", ")
        ));
    }
    let node_state = if result.node_budget_exhausted {
        "exhausted"
    } else {
        "available"
    };
    let edge_state = if result.edge_budget_exhausted {
        "exhausted"
    } else {
        "available"
    };
    lines.extend([
        String::new(),
        format!(
            "Budgets: nodes {}/{} ({node_state}); edges {}/{} ({edge_state})",
            result.nodes.len(),
            query.max_nodes,
            result.edges.len(),
            query.max_edges
        ),
    ]);
    format!("{}\n", lines.join("\n"))
}

fn node_label(identity: &str, nodes: &HashMap<&str, &MemoryGraphNode>) -> String {
    nodes.get(identity).map_or_else(
        || identity.to_owned(),
        |node| {
            format!(
                "{} <{identity}>",
                node.title.as_deref().unwrap_or(&node.basename)
            )
        },
    )
}
