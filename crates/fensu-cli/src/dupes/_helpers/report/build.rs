//! Detect exact, renamed, and near-miss function clones and group them into clusters.

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};

use crate::dupes::_helpers::contracts::forced::find_forced_overrides;
use crate::dupes::_helpers::inputs::changes::{collect_changes_since, unit_changed};
use crate::dupes::_helpers::inputs::globs::GlobList;
use crate::dupes::_helpers::matching::clustering::{cluster_pairs, ClusterContext};
use crate::dupes::_helpers::matching::pairs::find_clone_pairs;
use crate::dupes::_helpers::report::diff::member_diff;
use crate::dupes::_helpers::units::collection::collect_units;
use crate::dupes::models::{
    CloneCluster, ClonePair, CloneUnit, DupesOptions, DupesReport, DupesWorkspace,
};

pub(crate) fn build_report(
    workspace: &DupesWorkspace,
    options: &DupesOptions,
) -> Result<DupesReport, String> {
    let changes = options
        .since
        .as_deref()
        .map(|revision| collect_changes_since(&workspace.root, revision))
        .transpose()?;
    let path_filter = GlobList::new(&options.path_globs)?;
    let allowlist = workspace
        .config
        .allowlist
        .iter()
        .map(|entry| GlobList::new(&entry.paths))
        .collect::<Result<Vec<_>, String>>()?;
    let units = collect_units(
        &workspace.sources,
        options.include_tests,
        options.min_tokens,
    );
    let candidates = find_clone_pairs(&units, options.min_similarity);
    let forced = forced_units(workspace, &units, &candidates)?;
    let retained: Vec<ClonePair> = candidates
        .into_iter()
        .filter(|pair| !(forced.contains(&pair.left) && forced.contains(&pair.right)))
        .collect();
    let pairs: Vec<ClonePair> = retained
        .iter()
        .filter(|pair| !allowlisted(&allowlist, &units[pair.left], &units[pair.right]))
        .copied()
        .collect();
    let changed = |unit: &CloneUnit| {
        changes
            .as_ref()
            .is_some_and(|changes| unit_changed(unit, changes.get(&unit.path)))
    };
    let context = ClusterContext {
        units: &units,
        forced: &forced,
        changed: &changed,
    };
    let mut clusters: Vec<CloneCluster> = cluster_pairs(&context, &pairs)
        .into_iter()
        .filter(|cluster| cluster_selected(cluster, changes.is_some(), &path_filter))
        .collect();
    if options.diff {
        let sources: HashMap<&str, &[u8]> = workspace
            .sources
            .iter()
            .map(|source| (source.repository_path.as_str(), source.content.as_slice()))
            .collect();
        for cluster in clusters.iter_mut().take(options.top) {
            cluster.diff = member_diff(cluster, &sources);
        }
    }
    let retained_units = paired(&retained);
    let mut unit_counts: BTreeMap<&'static str, usize> = options
        .languages
        .iter()
        .map(|language| (*language, 0))
        .collect();
    for unit in &units {
        *unit_counts.entry(unit.language).or_default() += 1;
    }
    Ok(DupesReport {
        since: options.since.clone(),
        unit_counts,
        allowlisted_pairs: retained.len() - pairs.len(),
        contract_exempt_members: forced.difference(&retained_units).count(),
        clusters,
    })
}

fn forced_units(
    workspace: &DupesWorkspace,
    units: &[CloneUnit],
    candidates: &[ClonePair],
) -> Result<HashSet<usize>, String> {
    let paired_indexes: Vec<usize> = paired(candidates)
        .into_iter()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    let paired_units: Vec<&CloneUnit> = paired_indexes.iter().map(|index| &units[*index]).collect();
    let flags = find_forced_overrides(
        &workspace.root,
        &workspace.python_import_roots,
        &workspace.config.contract_exemptions,
        &paired_units,
    )?;
    Ok(paired_indexes
        .into_iter()
        .zip(flags)
        .filter_map(|(index, forced)| forced.then_some(index))
        .collect())
}

fn paired(pairs: &[ClonePair]) -> HashSet<usize> {
    pairs
        .iter()
        .flat_map(|pair| [pair.left, pair.right])
        .collect()
}

fn allowlisted(allowlist: &[GlobList], left: &CloneUnit, right: &CloneUnit) -> bool {
    allowlist
        .iter()
        .any(|globs| globs.matches(&left.path) && globs.matches(&right.path))
}

/// Keep clusters touching changed lines under `--since` and matching any `--path` glob.
fn cluster_selected(cluster: &CloneCluster, since: bool, path_filter: &GlobList) -> bool {
    let changed = !since || cluster.members.iter().any(|member| member.changed);
    let located = path_filter.is_empty()
        || cluster
            .members
            .iter()
            .any(|member| path_filter.matches(&member.path));
    changed && located
}
