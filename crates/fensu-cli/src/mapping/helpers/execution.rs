use std::env;
use std::io::{self, IsTerminal};
use std::path::Path;

use crate::mapping::helpers::{cache, index, project, render, tree};
use crate::mapping::models::{
    MapCacheStats, MapDirection, MapOptions, ProjectIndex, SourceSnapshot,
};
use crate::models::CliOutput;

pub(crate) fn execute(options: MapOptions) -> Result<CliOutput, String> {
    let mapping_project = project::resolve(&options.roots)?;
    let snapshots = project::discover(&mapping_project.sources, &mapping_project.repo_root)?;
    let cache_enabled = options
        .cache_enabled
        .unwrap_or(mapping_project.cache_enabled);
    let (project_index, stats) = if cache_enabled {
        let (index, stats) = cached_index(&mapping_project.repo_root, &snapshots)?;
        (index, Some(stats))
    } else {
        (index::build(&snapshots)?, None)
    };
    let root = index::select(&project_index.functions, &options.symbol)?;
    let call_tree = match options.direction {
        MapDirection::Downstream => tree::build_tree(root, &project_index, options.depth),
        MapDirection::Upstream => tree::build_upstream_tree(root, &project_index, options.depth),
    };
    let use_color = env::var_os("NO_COLOR").is_none()
        && match options.color.as_str() {
            "always" => true,
            "auto" => io::stdout().is_terminal(),
            _ => false,
        };
    let stdout = render::render(
        &call_tree,
        &mapping_project.repo_root,
        options.path_mode,
        use_color,
    );
    let stderr = cache_status(stats, options.cache_stats);
    Ok(CliOutput {
        stdout,
        stderr,
        exit_code: 0,
    })
}

fn cached_index(
    repo_root: &Path,
    snapshots: &[SourceSnapshot],
) -> Result<(ProjectIndex, MapCacheStats), String> {
    let generation = cache::generation(snapshots);
    let requested_manifest_hit = cache::manifest_hit(repo_root, &generation);
    let mut indexes = Vec::new();
    let mut missing = Vec::new();
    let mut reused = 0;
    for (snapshot, identity) in snapshots.iter().zip(&generation.file_identities) {
        if let Some(cached) = cache::read_file(repo_root, identity) {
            reused += 1;
            indexes.push(cached);
        } else {
            let indexed = index::build(std::slice::from_ref(snapshot))?;
            missing.push((identity.clone(), indexed.clone()));
            indexes.push(indexed);
        }
    }
    if requested_manifest_hit && missing.is_empty() {
        return Ok((
            index::merge(indexes),
            MapCacheStats {
                manifest_hit: true,
                ..MapCacheStats::default()
            },
        ));
    }
    let published = cache::publish(repo_root, &generation, &missing);
    Ok((
        index::merge(indexes),
        MapCacheStats {
            parsed_files: missing.len(),
            reused_file_records: reused,
            writes: if published { missing.len() + 1 } else { 0 },
            storage_failed: !published,
            ..MapCacheStats::default()
        },
    ))
}

fn cache_status(stats: Option<MapCacheStats>, show_stats: bool) -> String {
    let Some(stats) = stats else {
        return String::new();
    };
    let mut output = String::new();
    if stats.internal_error {
        output.push_str("Warning: an internal map cache error forced fresh mapping.\n");
    } else if stats.storage_failed {
        output.push_str("Warning: map cache publication failed; mapping output is complete.\n");
    }
    if show_stats {
        output.push_str(&cache::stats_text(stats));
    }
    output
}
