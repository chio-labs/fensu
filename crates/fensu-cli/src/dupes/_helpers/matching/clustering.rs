//! Group clone pairs into transitive clusters and rank them.

use std::collections::{BTreeMap, HashMap, HashSet};

use crate::dupes::_helpers::matching::sequence::to_f64;
use crate::dupes::constants::{CATEGORY_EXACT, CATEGORY_NEAR_MISS, CATEGORY_RENAMED};
use crate::dupes::models::{
    Category, CloneCluster, CloneMember, ClonePair, CloneUnit, ClusterLink,
};

/// Inputs that decide how units appear inside clusters.
pub(crate) struct ClusterContext<'a> {
    pub(crate) units: &'a [CloneUnit],
    pub(crate) forced: &'a HashSet<usize>,
    pub(crate) changed: &'a dyn Fn(&CloneUnit) -> bool,
}

/// Group pairs into connected components ordered by estimated duplicated tokens.
pub(crate) fn cluster_pairs(
    context: &ClusterContext<'_>,
    pairs: &[ClonePair],
) -> Vec<CloneCluster> {
    let mut clusters: Vec<CloneCluster> = connected_groups(pairs)
        .into_iter()
        .map(|component| build_cluster(context, &component))
        .collect();
    clusters.sort_by(|left, right| {
        right
            .duplicated_tokens
            .cmp(&left.duplicated_tokens)
            .then_with(|| right.similarity_max.total_cmp(&left.similarity_max))
            .then_with(|| left.members[0].path.cmp(&right.members[0].path))
            .then_with(|| left.members[0].start_line.cmp(&right.members[0].start_line))
    });
    clusters
}

pub(crate) const fn category_name(category: Category) -> &'static str {
    match category {
        Category::Exact => CATEGORY_EXACT,
        Category::Renamed => CATEGORY_RENAMED,
        Category::NearMiss => CATEGORY_NEAR_MISS,
    }
}

fn connected_groups(pairs: &[ClonePair]) -> Vec<Vec<ClonePair>> {
    let mut components = DisjointSet::default();
    for pair in pairs {
        components.union(pair.left, pair.right);
    }
    let mut grouped: BTreeMap<usize, Vec<ClonePair>> = BTreeMap::new();
    for pair in pairs {
        grouped
            .entry(components.root(pair.left))
            .or_default()
            .push(*pair);
    }
    grouped.into_values().collect()
}

#[derive(Default)]
struct DisjointSet {
    parent: HashMap<usize, usize>,
}

impl DisjointSet {
    fn root(&mut self, node: usize) -> usize {
        let mut current = node;
        while let Some(&next) = self.parent.get(&current) {
            if next == current {
                break;
            }
            current = next;
        }
        self.parent.insert(node, current);
        current
    }

    fn union(&mut self, left: usize, right: usize) {
        let (left, right) = (self.root(left), self.root(right));
        if left != right {
            self.parent.insert(left.max(right), left.min(right));
        }
    }
}

fn build_cluster(context: &ClusterContext<'_>, pairs: &[ClonePair]) -> CloneCluster {
    let units = context.units;
    let mut indexes: Vec<usize> = pairs
        .iter()
        .flat_map(|pair| [pair.left, pair.right])
        .collect::<HashSet<_>>()
        .into_iter()
        .collect();
    indexes.sort_by(|left, right| {
        let key = |index: &usize| {
            (
                context.forced.contains(index),
                &units[*index].path,
                units[*index].start_line,
                &units[*index].name,
            )
        };
        key(left).cmp(&key(right))
    });
    let slot: HashMap<usize, usize> = indexes
        .iter()
        .enumerate()
        .map(|(position, index)| (*index, position))
        .collect();
    let mut best: HashMap<usize, f64> = HashMap::new();
    for pair in pairs {
        for index in [pair.left, pair.right] {
            let entry = best.entry(index).or_insert(0.0);
            *entry = entry.max(pair.similarity);
        }
    }
    let weights: Vec<f64> = indexes
        .iter()
        .filter(|index| !context.forced.contains(index))
        .map(|index| to_f64(units[*index].tokens.len()) * best[index])
        .collect();
    let mut links: Vec<ClusterLink> = pairs
        .iter()
        .map(|pair| {
            let (left, right) = (slot[&pair.left], slot[&pair.right]);
            ClusterLink {
                left: left.min(right),
                right: left.max(right),
                similarity: pair.similarity,
                category: category_name(pair.category),
            }
        })
        .collect();
    links.sort_by_key(|link| (link.left, link.right));
    let members: Vec<CloneMember> = indexes
        .iter()
        .map(|index| {
            let unit = &units[*index];
            CloneMember {
                language: unit.language,
                path: unit.path.clone(),
                name: unit.name.clone(),
                start_line: unit.start_line,
                end_line: unit.end_line,
                tokens: unit.tokens.len(),
                changed: (context.changed)(unit),
                forced: context.forced.contains(index),
            }
        })
        .collect();
    let category = pairs
        .iter()
        .map(|pair| pair.category)
        .max()
        .unwrap_or(Category::Exact);
    CloneCluster {
        category: category_name(category),
        similarity_min: pairs.iter().map(|pair| pair.similarity).fold(1.0, f64::min),
        similarity_max: pairs.iter().map(|pair| pair.similarity).fold(0.0, f64::max),
        duplicated_tokens: duplicated_tokens(&weights, weights.len() < members.len()),
        members,
        links,
        diff: None,
    }
}

/// Estimate removable tokens: keep one copy, or a required forced override when present.
fn duplicated_tokens(weights: &[f64], has_forced: bool) -> usize {
    let total: f64 = weights.iter().sum();
    let kept = if has_forced {
        0.0
    } else {
        weights.iter().copied().fold(0.0, f64::max)
    };
    (total - kept).round().max(0.0) as usize
}
