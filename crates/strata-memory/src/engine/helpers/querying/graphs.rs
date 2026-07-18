//! Root resolution and bounded deterministic graph traversal.

use std::collections::{HashMap, HashSet, VecDeque};
use std::path::Path;

use rusqlite::{Connection, OpenFlags};

use crate::engine::constants::{
    ARCHIVE_STATE_ACTIVE, ARCHIVE_STATE_ARCHIVED, RESOLUTION_STATUS_RESOLVED,
};
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::querying::graph_loading::{
    load_documents, load_links, DocumentRow, LinkRow,
};
use crate::engine::models::{
    MemoryGraphDirection, MemoryGraphEdge, MemoryGraphNode, MemoryGraphQuery, MemoryGraphResult,
};

const MIN_DEPTH: usize = 1;
const MAX_DEPTH: usize = 5;
const MIN_NODES: usize = 1;
const MAX_NODES: usize = 200;
const MIN_EDGES: usize = 1;
const MAX_EDGES: usize = 500;

pub(crate) fn run(
    database_path: &Path,
    query: &MemoryGraphQuery,
) -> Result<MemoryGraphResult, MemoryIndexError> {
    validate(query)?;
    if !database_path.is_file() {
        return Err(MemoryIndexError::DatabaseNotFound(
            database_path.to_path_buf(),
        ));
    }
    let connection =
        Connection::open_with_flags(database_path, OpenFlags::SQLITE_OPEN_READ_ONLY)
            .map_err(|error| MemoryIndexError::sqlite("open read-only memory index", error))?;
    traverse(&connection, query)
}

fn validate(query: &MemoryGraphQuery) -> Result<(), MemoryIndexError> {
    if query.pattern.trim().is_empty() {
        return Err(MemoryIndexError::GraphQuery(
            "document or pattern must not be empty".to_owned(),
        ));
    }
    validate_range("depth", query.depth, MIN_DEPTH, MAX_DEPTH)?;
    validate_range("max nodes", query.max_nodes, MIN_NODES, MAX_NODES)?;
    validate_range("max edges", query.max_edges, MIN_EDGES, MAX_EDGES)
}

fn validate_range(
    name: &str,
    value: usize,
    minimum: usize,
    maximum: usize,
) -> Result<(), MemoryIndexError> {
    if (minimum..=maximum).contains(&value) {
        return Ok(());
    }
    Err(MemoryIndexError::GraphQuery(format!(
        "{name} {value} is invalid; expected {minimum}..={maximum}"
    )))
}

fn traverse(
    connection: &Connection,
    query: &MemoryGraphQuery,
) -> Result<MemoryGraphResult, MemoryIndexError> {
    let documents = load_documents(connection)?;
    let links = load_links(connection, &query.relationships)?;
    let (selection, matched_roots) = resolve_roots(&documents, query)?;
    let node_budget_exhausted = matched_roots.len() > query.max_nodes;
    let roots = matched_roots
        .into_iter()
        .take(query.max_nodes)
        .collect::<Vec<String>>();
    let by_identity = documents
        .into_iter()
        .map(|document| (document.identity.clone(), document))
        .collect::<HashMap<String, DocumentRow>>();
    let mut state = TraversalState::new(&roots, &by_identity);
    walk(&mut state, &by_identity, &links, query);
    mark_cycles(&mut state.edges);
    state
        .nodes
        .sort_by(|left, right| left.identity.cmp(&right.identity));
    state.edges.sort_by(|left, right| {
        (&left.source_document_identity, left.source_link_ordinal)
            .cmp(&(&right.source_document_identity, right.source_link_ordinal))
    });
    Ok(MemoryGraphResult {
        selection,
        roots,
        nodes: state.nodes,
        edges: state.edges,
        node_budget_exhausted: node_budget_exhausted || state.node_budget_exhausted,
        edge_budget_exhausted: state.edge_budget_exhausted,
    })
}

struct TraversalState {
    queue: VecDeque<(String, usize)>,
    discovered: HashSet<String>,
    emitted_edges: HashSet<(String, usize)>,
    nodes: Vec<MemoryGraphNode>,
    edges: Vec<MemoryGraphEdge>,
    node_budget_exhausted: bool,
    edge_budget_exhausted: bool,
}

impl TraversalState {
    fn new(roots: &[String], documents: &HashMap<String, DocumentRow>) -> Self {
        let root_set = roots.iter().cloned().collect::<HashSet<String>>();
        let nodes = roots
            .iter()
            .filter_map(|identity| documents.get(identity))
            .map(|document| graph_node(document, 0, true))
            .collect::<Vec<MemoryGraphNode>>();
        let queue = roots
            .iter()
            .cloned()
            .map(|identity| (identity, 0))
            .collect::<VecDeque<(String, usize)>>();
        Self {
            queue,
            discovered: root_set,
            emitted_edges: HashSet::new(),
            nodes,
            edges: Vec::new(),
            node_budget_exhausted: false,
            edge_budget_exhausted: false,
        }
    }
}

fn walk(
    state: &mut TraversalState,
    documents: &HashMap<String, DocumentRow>,
    links: &[LinkRow],
    query: &MemoryGraphQuery,
) {
    while let Some((identity, depth)) = state.queue.pop_front() {
        if depth >= query.depth || !can_expand(&identity, documents, query.include_archived) {
            continue;
        }
        let candidates = candidate_links(&identity, links, query.direction);
        for link in candidates {
            let edge_key = (link.source.clone(), link.ordinal);
            if state.emitted_edges.contains(&edge_key) {
                continue;
            }
            if state.edges.len() == query.max_edges {
                state.edge_budget_exhausted = true;
                continue;
            }
            state.emitted_edges.insert(edge_key);
            state.edges.push(graph_edge(link));
            let Some(neighbor) = neighbor_identity(&identity, link, query.direction) else {
                continue;
            };
            if state.discovered.contains(neighbor) {
                continue;
            }
            if state.nodes.len() == query.max_nodes {
                state.node_budget_exhausted = true;
                continue;
            }
            let Some(document) = documents.get(neighbor) else {
                continue;
            };
            state.discovered.insert(neighbor.to_owned());
            state.nodes.push(graph_node(document, depth + 1, false));
            if query.include_archived || document.archive_state == ARCHIVE_STATE_ACTIVE {
                state.queue.push_back((neighbor.to_owned(), depth + 1));
            }
        }
    }
}

fn can_expand(
    identity: &str,
    documents: &HashMap<String, DocumentRow>,
    include_archived: bool,
) -> bool {
    include_archived
        || documents
            .get(identity)
            .is_some_and(|document| document.archive_state == ARCHIVE_STATE_ACTIVE)
}

fn candidate_links<'a>(
    identity: &str,
    links: &'a [LinkRow],
    direction: MemoryGraphDirection,
) -> Vec<&'a LinkRow> {
    let mut selected = links
        .iter()
        .filter(|link| match direction {
            MemoryGraphDirection::Outbound => link.source == identity,
            MemoryGraphDirection::Inbound => {
                link.status == RESOLUTION_STATUS_RESOLVED
                    && link.target_identity.as_deref() == Some(identity)
            }
            MemoryGraphDirection::Both => {
                link.source == identity
                    || (link.status == RESOLUTION_STATUS_RESOLVED
                        && link.target_identity.as_deref() == Some(identity))
            }
        })
        .collect::<Vec<&LinkRow>>();
    selected
        .sort_by(|left, right| (&left.source, left.ordinal).cmp(&(&right.source, right.ordinal)));
    selected
}

fn neighbor_identity<'a>(
    current: &str,
    link: &'a LinkRow,
    direction: MemoryGraphDirection,
) -> Option<&'a str> {
    if link.status != RESOLUTION_STATUS_RESOLVED {
        return None;
    }
    if link.source == current && direction != MemoryGraphDirection::Inbound {
        return link.target_identity.as_deref();
    }
    if link.target_identity.as_deref() == Some(current)
        && direction != MemoryGraphDirection::Outbound
    {
        return Some(link.source.as_str());
    }
    None
}

fn resolve_roots(
    documents: &[DocumentRow],
    query: &MemoryGraphQuery,
) -> Result<(String, Vec<String>), MemoryIndexError> {
    let eligible = documents
        .iter()
        .filter(|document| query.include_archived || document.archive_state == ARCHIVE_STATE_ACTIVE)
        .collect::<Vec<&DocumentRow>>();
    let exact = eligible
        .iter()
        .filter(|document| fields(document).iter().any(|value| *value == query.pattern))
        .map(|document| document.identity.clone())
        .collect::<Vec<String>>();
    if exact.len() > 1 {
        return Err(MemoryIndexError::GraphQuery(format!(
            "document selector {:?} exactly matches multiple documents: {}",
            query.pattern,
            exact.join(", ")
        )));
    }
    if !exact.is_empty() {
        return Ok(("exact".to_owned(), exact));
    }
    let needle = query.pattern.to_lowercase();
    let substring = eligible
        .iter()
        .filter(|document| {
            fields(document)
                .iter()
                .any(|value| value.to_lowercase().contains(&needle))
        })
        .map(|document| document.identity.clone())
        .collect::<Vec<String>>();
    if !substring.is_empty() {
        return Ok(("substring".to_owned(), substring));
    }
    let archived_match = documents.iter().any(|document| {
        document.archive_state == ARCHIVE_STATE_ARCHIVED
            && fields(document)
                .iter()
                .any(|value| value.to_lowercase().contains(&needle))
    });
    let suffix = if archived_match && !query.include_archived {
        "; matching documents are archived, use --include-archived"
    } else {
        ""
    };
    Err(MemoryIndexError::GraphQuery(format!(
        "no memory documents match {:?}{suffix}",
        query.pattern
    )))
}

fn fields(document: &DocumentRow) -> [&str; 5] {
    [
        document.identity.as_str(),
        document.repository_relative_path.as_str(),
        document.basename.as_str(),
        document.slug.as_str(),
        document.title.as_deref().unwrap_or(""),
    ]
}

fn graph_node(document: &DocumentRow, depth: usize, root: bool) -> MemoryGraphNode {
    MemoryGraphNode {
        identity: document.identity.clone(),
        artifact_kind: document.artifact_kind.clone(),
        archive_state: document.archive_state.clone(),
        repository_relative_path: document.repository_relative_path.clone(),
        basename: document.basename.clone(),
        slug: document.slug.clone(),
        title: document.title.clone(),
        depth,
        root,
    }
}

fn graph_edge(link: &LinkRow) -> MemoryGraphEdge {
    MemoryGraphEdge {
        source_document_identity: link.source.clone(),
        source_link_ordinal: link.ordinal,
        relationship: link.relationship.clone(),
        authored_target: link.target.clone(),
        resolution_status: link.status.clone(),
        target_document_identity: link.target_identity.clone(),
        cycle: false,
    }
}

fn mark_cycles(edges: &mut [MemoryGraphEdge]) {
    let adjacency = edges
        .iter()
        .filter_map(|edge| {
            edge.target_document_identity
                .as_ref()
                .filter(|_| edge.resolution_status == RESOLUTION_STATUS_RESOLVED)
                .map(|target| (edge.source_document_identity.clone(), target.clone()))
        })
        .fold(
            HashMap::<String, Vec<String>>::new(),
            |mut values, (source, target)| {
                values.entry(source).or_default().push(target);
                values
            },
        );
    for edge in edges {
        let Some(target) = edge.target_document_identity.as_deref() else {
            continue;
        };
        edge.cycle = has_path(target, &edge.source_document_identity, &adjacency);
    }
}

fn has_path(start: &str, goal: &str, adjacency: &HashMap<String, Vec<String>>) -> bool {
    let mut pending = vec![start];
    let mut visited = HashSet::new();
    while let Some(current) = pending.pop() {
        if current == goal {
            return true;
        }
        if !visited.insert(current) {
            continue;
        }
        if let Some(targets) = adjacency.get(current) {
            pending.extend(targets.iter().map(String::as_str));
        }
    }
    false
}
