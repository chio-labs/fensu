//! Dependency plans for non-file native role layout rules.

use std::path::Path;

use crate::rules::constants::{
    HELPERS_PACKAGE_LAYOUT_CODE, LEAF_MAIN_BOUNDARY_CODE, MAIN_PACKAGE_LAYOUT_CODE,
    SHARED_DOMAIN_PREFIX_CODE, TOP_LEVEL_DOMAIN_SHAPE_CODE,
};
use crate::rules::helpers::role_project_layout_paths::{
    direct_modules, directory_entries, domain_dir, file_name, leaf_dir, main_entries, mixed_domain,
    named_subdomains, prefix_candidates, prefix_groups, python_anchor, repository_path, role_name,
    role_package, scope_root, HELPERS, INIT_FILE, PYTHON_CACHE,
};
use crate::rules::models::{NativeProjectQuery, NativeRuleContext};

const MAIN_ROLE: &str = "main";
const MINIMUM_SHARED_PREFIX_THRESHOLD: &str = "min_shared_domain_prefix_packages";
const PYTHON_GLOB: &str = "*.py";

pub(crate) fn project_layout_queries(
    code: &str,
    context: &NativeRuleContext,
) -> Option<Vec<NativeProjectQuery>> {
    let mut queries = Vec::new();
    match code {
        HELPERS_PACKAGE_LAYOUT_CODE | MAIN_PACKAGE_LAYOUT_CODE => {
            let role = if code == HELPERS_PACKAGE_LAYOUT_CODE {
                HELPERS
            } else {
                MAIN_ROLE
            };
            let Some(package) = role_package(context, role) else {
                return Some(queries);
            };
            let container = repository_path(context)
                .parent()
                .map(Path::to_path_buf)
                .unwrap_or_default();
            if context.relative_parts.last().map(String::as_str) != Some(INIT_FILE) {
                queries.push(query("exists", &container.join(INIT_FILE), ""));
            }
            queries.push(glob_query(&container, false));
            if !direct_modules(&container).is_empty() {
                queries.push(glob_query(&container, true));
            }
            if container != package {
                let mut ancestor = container.parent();
                while let Some(path) = ancestor {
                    if path == package {
                        break;
                    }
                    queries.push(query("python_anchor", path, ""));
                    if python_anchor(path).as_deref() != Some(repository_path(context).as_path()) {
                        break;
                    }
                    ancestor = path.parent();
                }
            }
        }
        TOP_LEVEL_DOMAIN_SHAPE_CODE => {
            let Some(domain) = domain_dir(context) else {
                return Some(queries);
            };
            queries.push(query("directory_entries", &domain, ""));
            append_subdomain_queries(&mut queries, &domain);
            if mixed_domain(&domain) {
                queries.push(query("is_file", &domain.join(INIT_FILE), ""));
                if !domain.join(INIT_FILE).is_file() {
                    queries.push(glob_query(&domain, true));
                }
            }
        }
        SHARED_DOMAIN_PREFIX_CODE => {
            let root = scope_root(context);
            queries.push(query("is_file", &root.join(INIT_FILE), ""));
            if !root.join(INIT_FILE).is_file() {
                queries.push(glob_query(&root, true));
            }
            if context
                .thresholds
                .get(MINIMUM_SHARED_PREFIX_THRESHOLD)
                .copied()
                .unwrap_or_default()
                > 0
            {
                queries.push(query("directory_entries", &root, ""));
                for entry in prefix_candidates(&root) {
                    queries.push(query("is_dir", &entry, ""));
                    if entry.is_dir() {
                        queries.push(glob_query(&entry, true));
                    }
                }
                for (prefix, names) in prefix_groups(&root) {
                    let minimum = context.thresholds[MINIMUM_SHARED_PREFIX_THRESHOLD] as usize;
                    if names.len() >= minimum {
                        queries.push(query("is_dir", &root.join(prefix), ""));
                    }
                }
            }
        }
        LEAF_MAIN_BOUNDARY_CODE => {
            let Some(leaf) = leaf_dir(context) else {
                return Some(queries);
            };
            let domain = scope_root(context).join(&context.relative_parts[0]);
            if leaf == domain {
                queries.push(query("directory_entries", &domain, ""));
                append_subdomain_queries(&mut queries, &domain);
                if !named_subdomains(&domain).is_empty() {
                    return Some(queries);
                }
            }
            queries.push(glob_query(&leaf.join(MAIN_ROLE), true));
            if main_entries(&leaf).is_empty() {
                queries.push(query("python_anchor", &leaf, ""));
            }
        }
        _ => return None,
    }
    Some(queries)
}

fn append_subdomain_queries(queries: &mut Vec<NativeProjectQuery>, domain: &Path) {
    for entry in directory_entries(domain) {
        if role_name(&entry) || file_name(&entry) == PYTHON_CACHE {
            continue;
        }
        queries.push(query("is_dir", &entry, ""));
        if entry.is_dir() {
            queries.push(glob_query(&entry, true));
        }
    }
}

fn query(kind: &str, path: &Path, argument: &str) -> NativeProjectQuery {
    NativeProjectQuery {
        kind: kind.to_owned(),
        path: path.to_string_lossy().replace('\\', "/"),
        argument: argument.to_owned(),
    }
}

fn glob_query(path: &Path, recursive: bool) -> NativeProjectQuery {
    query("glob", path, &format!("{PYTHON_GLOB}\0{recursive}"))
}
