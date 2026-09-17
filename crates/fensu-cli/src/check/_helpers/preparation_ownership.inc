// Resolve path-scoped ownership roots before analyzer policy runs.

type Specificity = (usize, usize, usize);
type OwnershipDeclaration = (Specificity, usize, String);

const STRUCTURAL_ROLE_DIRECTORIES: &[&str] = &["main", "_helpers", "classes"];
const GLOB_CHARACTERS: &str = "*?[]";

fn resolve_ownership_roots(
    project_root: &Path,
    config: &Config,
) -> Result<Vec<ResolvedOwnershipRoot>, String> {
    if config.ownership_roots.is_empty() {
        return Ok(implicit(config));
    }
    let mut directories: Vec<String> = Vec::new();
    for result in WalkDir::new(project_root).follow_links(false) {
        let entry = result.map_err(|error| error.to_string())?;
        if !entry.file_type().is_dir() {
            continue;
        }
        let relative = entry
            .path()
            .strip_prefix(project_root)
            .map_err(|error| error.to_string())?;
        directories.push(relative.to_string_lossy().replace('\\', "/"));
    }
    let mut matches: HashMap<String, Vec<OwnershipDeclaration>> = HashMap::new();
    for (index, pattern) in config.ownership_roots.iter().enumerate() {
        let matched = directories
            .iter()
            .filter(|path| ownership_path_matches(path, pattern))
            .cloned()
            .collect::<Vec<_>>();
        if matched.is_empty() {
            return Err(format!(
                "Configured ownership root pattern matched no directories: {pattern}"
            ));
        }
        let specificity = specificity(pattern);
        for path in matched {
            let source_root = config
                .roots
                .iter()
                .filter(|root| path_is_within(&path, root))
                .max_by_key(|root| root.split('/').count());
            let Some(source_root) = source_root else {
                return Err(format!(
                    "Configured ownership root must resolve beneath a runtime root: {pattern}"
                ));
            };
            let relative = relative_ownership_path(&path, source_root);
            if relative
                .split('/')
                .any(|part| STRUCTURAL_ROLE_DIRECTORIES.contains(&part))
            {
                return Err(format!(
                    "Configured ownership root crosses a role directory: {pattern}"
                ));
            }
            if !contains_supported_source(project_root, &path, config.analyzer) {
                return Err(format!(
                    "Configured ownership root contains no analyzable files: {path}"
                ));
            }
            matches
                .entry(path)
                .or_default()
                .push((specificity, index, pattern.clone()));
        }
    }
    let mut resolved: Vec<ResolvedOwnershipRoot> = Vec::new();
    let mut selected_declarations: Vec<bool> = vec![false; config.ownership_roots.len()];
    for (path, declarations) in matches {
        let best_specificity = declarations
            .iter()
            .map(|(specificity, _, _)| *specificity)
            .max()
            .unwrap_or_default();
        let best = declarations
            .iter()
            .filter(|(specificity, _, _)| *specificity == best_specificity)
            .collect::<Vec<_>>();
        if best.len() > 1 {
            let patterns = best
                .iter()
                .map(|(_, _, pattern)| pattern.as_str())
                .collect::<Vec<_>>()
                .join(", ");
            return Err(format!(
                "Ownership root has equal-specificity declarations for {path}: {patterns}"
            ));
        }
        let (_, index, pattern) = best[0];
        selected_declarations[*index] = true;
        resolved.push(ResolvedOwnershipRoot {
            path,
            declaration: format!("ownership_roots[{index}] ({pattern})"),
        });
    }
    let unused_declarations = config
        .ownership_roots
        .iter()
        .zip(selected_declarations)
        .filter_map(|(pattern, selected)| (!selected).then_some(pattern.as_str()))
        .collect::<Vec<_>>();
    if !unused_declarations.is_empty() {
        return Err(format!(
            "Configured ownership root declaration is unused: {}",
            unused_declarations.join(", ")
        ));
    }
    resolved.sort_by(|left, right| left.path.cmp(&right.path));
    validate_ownership_root_usage(project_root, config.analyzer, &resolved)?;
    Ok(resolved)
}

fn ownership_path_matches(path: &str, pattern: &str) -> bool {
    crate::configuration::main::expand_path_pattern::expand_path_pattern(pattern).is_ok_and(
        |patterns| {
            patterns.iter().any(|expanded| {
                globset::GlobBuilder::new(expanded)
                    .literal_separator(true)
                    .backslash_escape(false)
                    .build()
                    .is_ok_and(|glob| glob.compile_matcher().is_match(path))
            })
        },
    )
}

fn contains_supported_source(project_root: &Path, relative: &str, analyzer: AnalyzerId) -> bool {
    WalkDir::new(project_root.join(relative))
        .follow_links(false)
        .into_iter()
        .filter_map(Result::ok)
        .any(|entry| {
            entry.file_type().is_file() && supported_source(entry.path(), analyzer)
        })
}

fn specificity(pattern: &str) -> Specificity {
    let mut literal_parts: usize = 0;
    let mut literal_characters: usize = 0;
    let mut glob_characters: usize = 0;
    for part in pattern.split('/') {
        let mut part_contains_glob: bool = false;
        for character in part.chars() {
            if GLOB_CHARACTERS.contains(character) {
                part_contains_glob = true;
                glob_characters += 1;
            } else {
                literal_characters += 1;
            }
        }
        if !part_contains_glob {
            literal_parts += 1;
        }
    }
    (
        literal_parts,
        literal_characters,
        usize::MAX - glob_characters,
    )
}

fn validate_ownership_root_usage(
    project_root: &Path,
    analyzer: AnalyzerId,
    roots: &[ResolvedOwnershipRoot],
) -> Result<(), String> {
    let mut used: Vec<String> = Vec::new();
    for result in WalkDir::new(project_root).follow_links(false) {
        let entry = result.map_err(|error| error.to_string())?;
        if !entry.file_type().is_file() || !supported_source(entry.path(), analyzer) {
            continue;
        }
        let path = entry
            .path()
            .strip_prefix(project_root)
            .map_err(|error| error.to_string())?
            .to_string_lossy()
            .replace('\\', "/");
        let root = roots
            .iter()
            .filter(|root| path_is_within(&path, &root.path))
            .max_by_key(|root| root.path.split('/').count());
        let Some(root) = root else {
            continue;
        };
        used.push(root.path.clone());
    }
    used.sort();
    used.dedup();
    let unused = roots
        .iter()
        .filter(|root| used.binary_search(&root.path).is_err())
        .map(|root| root.path.as_str())
        .collect::<Vec<_>>();
    if unused.is_empty() {
        Ok(())
    } else {
        Err(format!(
            "Configured ownership root is unused: {}",
            unused.join(", ")
        ))
    }
}

fn supported_source(path: &Path, analyzer: AnalyzerId) -> bool {
    match analyzer {
        AnalyzerId::Python => path.extension().and_then(|value| value.to_str()) == Some("py"),
        AnalyzerId::Rust => path.extension().and_then(|value| value.to_str()) == Some("rs"),
        analyzer => web::is_web_source(path, analyzer),
    }
}

fn effective_ownership_root<'a>(
    path: &str,
    config: &'a Config,
) -> Option<&'a ResolvedOwnershipRoot> {
    config
        .resolved_ownership_roots
        .iter()
        .filter(|root| path_is_within(path, &root.path))
        .max_by_key(|root| root.path.split('/').count())
}

fn ownership_relative_parts(path: &str, root: &str) -> Vec<String> {
    relative_ownership_path(path, root)
        .split('/')
        .filter(|part| !part.is_empty())
        .map(str::to_owned)
        .collect()
}

fn implicit(config: &Config) -> Vec<ResolvedOwnershipRoot> {
    if config.analyzer == AnalyzerId::Rust {
        return Vec::new();
    }
    config
        .roots
        .iter()
        .enumerate()
        .map(|(index, root)| ResolvedOwnershipRoot {
            path: if matches!(config.analyzer, AnalyzerId::TypeScript | AnalyzerId::Svelte) {
                join_relative(root, "lib")
            } else {
                root.clone()
            },
            declaration: format!("roots[{index}]"),
        })
        .collect()
}

fn path_is_within(path: &str, root: &str) -> bool {
    root == CURRENT_PATH || path == root || path.starts_with(&format!("{root}/"))
}

fn relative_ownership_path<'a>(path: &'a str, root: &str) -> &'a str {
    if root == CURRENT_PATH {
        return path;
    }
    path.strip_prefix(root)
        .and_then(|value| value.strip_prefix('/'))
        .unwrap_or_default()
}

fn join_relative(root: &str, child: &str) -> String {
    if root == CURRENT_PATH {
        child.to_owned()
    } else {
        format!("{root}/{child}")
    }
}
