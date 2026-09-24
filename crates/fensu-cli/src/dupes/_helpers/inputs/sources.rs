//! Resolve analysable files from the configured targets and the `[dupes]` exclusions.

use std::collections::BTreeMap;
use std::path::Path;

use crate::analyzer::AnalyzerId;
use crate::check::main::discover_target_sources::discover_target_sources;
use crate::configuration::main::load_config_section::load_config_section;
use crate::configuration::main::load_targets::load_targets;
use crate::configuration::main::resolve_target_root::resolve_target_root;
use crate::constants::CURRENT_PATH as CURRENT_DIRECTORY;
use crate::dupes::_helpers::inputs::config::parse_dupes_config;
use crate::dupes::_helpers::inputs::globs::GlobList;
use crate::dupes::constants::{
    CONFIG_DUPES_KEY, LANGUAGE_JAVASCRIPT, LANGUAGE_PYTHON, LANGUAGE_RUST, LANGUAGE_SVELTE,
    LANGUAGE_TYPESCRIPT, RUST_TEST_DIRECTORIES, SCOPE_TEST,
};
use crate::dupes::models::{DupesOptions, DupesSource, DupesWorkspace};
use crate::models::ScopedSource;

/// Discover every configured target's sources once, keyed by repository path.
pub(crate) fn discover_workspace(
    invocation: &Path,
    options: &DupesOptions,
) -> Result<DupesWorkspace, String> {
    let loaded = load_targets(invocation, None)?;
    let (config_path, section) = load_config_section(invocation, CONFIG_DUPES_KEY)?;
    let config = parse_dupes_config(section.as_ref())?;
    let root = dunce::canonicalize(
        config_path
            .parent()
            .ok_or_else(|| "Configuration has no parent directory.".to_owned())?,
    )
    .map_err(|error| error.to_string())?;
    let excluded = GlobList::new(&config.exclude)?;
    let mut sources: BTreeMap<String, DupesSource> = BTreeMap::new();
    let mut python_import_roots: Vec<String> = Vec::new();
    for (_, target) in &loaded {
        let project_root = resolve_target_root(&root, &target.target_root)?;
        if target.analyzer == AnalyzerId::Python {
            python_import_roots.extend(import_roots(&target.target_root, &target.roots));
        }
        for source in discover_target_sources(&root, &project_root, target)? {
            let Some(language) = source_language(&source.repository_path) else {
                continue;
            };
            let test = is_test_source(&source, language);
            let selected = options.languages.contains(&language)
                && (options.include_tests || !test)
                && !excluded.matches(&source.repository_path);
            if selected {
                sources
                    .entry(source.repository_path.clone())
                    .or_insert_with(|| DupesSource {
                        path: source.path.clone(),
                        repository_path: source.repository_path.clone(),
                        language,
                        content: source.content,
                    });
            }
        }
    }
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    python_import_roots.retain(|root| seen.insert(root.clone()));
    Ok(DupesWorkspace {
        root,
        sources: sources.into_values().collect(),
        python_import_roots,
        config,
    })
}

/// Classify a repository path by file extension; declaration files have no bodies.
pub(crate) fn source_language(path: &str) -> Option<&'static str> {
    if [".d.ts", ".d.mts", ".d.cts"]
        .iter()
        .any(|suffix| path.ends_with(suffix))
    {
        return None;
    }
    let extension = path.rsplit_once('.').map(|(_, extension)| extension)?;
    Some(match extension {
        "py" => LANGUAGE_PYTHON,
        "rs" => LANGUAGE_RUST,
        "svelte" => LANGUAGE_SVELTE,
        "ts" | "tsx" | "mts" | "cts" => LANGUAGE_TYPESCRIPT,
        "js" | "jsx" | "mjs" | "cjs" => LANGUAGE_JAVASCRIPT,
        _ => return None,
    })
}

fn is_test_source(source: &ScopedSource, language: &str) -> bool {
    source.scope == SCOPE_TEST
        || language == LANGUAGE_RUST
            && source
                .target_path
                .split('/')
                .any(|part| RUST_TEST_DIRECTORIES.contains(&part))
}

/// Python import roots: each configured package root's parent, then the target root itself.
fn import_roots(target_root: &str, roots: &[String]) -> Vec<String> {
    let join = |path: &str| {
        let parts: Vec<&str> = [target_root, path]
            .into_iter()
            .flat_map(|part| part.split('/'))
            .filter(|part| !part.is_empty() && *part != CURRENT_DIRECTORY)
            .collect();
        parts.join("/")
    };
    let mut resolved: Vec<String> = roots
        .iter()
        .map(|root| join(root.rsplit_once('/').map_or("", |(parent, _)| parent)))
        .collect();
    resolved.push(join(""));
    resolved
}
