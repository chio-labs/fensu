//! Deterministic strongly connected dependency components.

use std::collections::{BTreeMap, BTreeSet};

use crate::source::models::DocumentIdentity;

pub(crate) fn components(
    adjacency: &BTreeMap<DocumentIdentity, BTreeSet<DocumentIdentity>>,
) -> Vec<Vec<DocumentIdentity>> {
    let mut components: BTreeSet<Vec<DocumentIdentity>> = BTreeSet::new();
    for node in adjacency.keys() {
        let members: Vec<DocumentIdentity> = adjacency
            .keys()
            .filter(|candidate| {
                reachable(adjacency, node, candidate) && reachable(adjacency, candidate, node)
            })
            .cloned()
            .collect();
        if members.len() > 1 {
            let _ = components.insert(members);
        }
    }
    components.into_iter().collect()
}

fn reachable(
    adjacency: &BTreeMap<DocumentIdentity, BTreeSet<DocumentIdentity>>,
    start: &DocumentIdentity,
    target: &DocumentIdentity,
) -> bool {
    let mut visited: BTreeSet<DocumentIdentity> = BTreeSet::new();
    let mut pending = vec![start.clone()];
    while let Some(node) = pending.pop() {
        if &node == target {
            return true;
        }
        if !visited.insert(node.clone()) {
            continue;
        }
        if let Some(neighbors) = adjacency.get(&node) {
            pending.extend(neighbors.iter().rev().cloned());
        }
    }
    false
}
