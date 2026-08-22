//! Validate configured crate identities and structural paths against a workspace.

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

use crate::constants;
use crate::models;

struct ConfiguredDirectoryRequest<'a> {
    repo_root: &'a Path,
    source_roots: &'a [std::path::PathBuf],
    configured: &'a str,
    kind: &'a str,
    require_role_name: bool,
}

pub(crate) fn check(
    repo_root: &Path,
    crates: &[models::WorkspaceCrate],
    config: &models::RepositoryPolicyConfig,
) -> Vec<models::Violation> {
    let mut violations = crate_name_violations(repo_root, crates, config);
    violations.extend(path_violations(repo_root, crates, config));
    violations
}

fn crate_name_violations(
    repo_root: &Path,
    crates: &[models::WorkspaceCrate],
    config: &models::RepositoryPolicyConfig,
) -> Vec<models::Violation> {
    if config.crate_names.is_empty() {
        return Vec::new();
    }
    let mut violations = crates
        .iter()
        .filter(|workspace_crate| {
            workspace_crate
                .package_name
                .as_ref()
                .is_none_or(|name| !config.crate_names.contains(name))
        })
        .map(|workspace_crate| {
            let manifest = workspace_crate
                .directory
                .join(constants::CARGO_MANIFEST_FILE);
            let relative = manifest.strip_prefix(repo_root).unwrap_or(&manifest);
            models::Violation::new(models::ViolationRequest {
                code: "RSL304",
                path: relative,
                line: None,
                message: format!(
                    "workspace package {} is not declared by repository policy",
                    workspace_crate
                        .package_name
                        .as_deref()
                        .unwrap_or("<unknown>")
                ),
                remediation:
                    "add the package to repository.crate-names or remove it from the workspace",
            })
        })
        .collect::<Vec<_>>();
    for configured in &config.crate_names {
        if crates
            .iter()
            .any(|workspace_crate| workspace_crate.package_name.as_ref() == Some(configured))
        {
            continue;
        }
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSL304",
            path: Path::new(constants::CARGO_MANIFEST_FILE),
            line: None,
            message: format!(
                "repository policy declares workspace package {configured}, but it is absent"
            ),
            remediation:
                "remove the stale repository.crate-names entry or add the package to the workspace",
        }));
    }
    violations
}

fn path_violations(
    repo_root: &Path,
    crates: &[models::WorkspaceCrate],
    config: &models::RepositoryPolicyConfig,
) -> Vec<models::Violation> {
    let source_roots = crates
        .iter()
        .flat_map(|workspace_crate| workspace_crate.targets.iter())
        .filter(|target| !target.test)
        .map(|target| target.source_root.clone())
        .collect::<Vec<_>>();
    let mut violations: Vec<models::Violation> = Vec::new();
    for path in &config.domain_paths {
        violations.extend(configured_directory_violation(ConfiguredDirectoryRequest {
            repo_root,
            source_roots: &source_roots,
            configured: path,
            kind: "domain",
            require_role_name: false,
        }));
    }
    for path in &config.role_paths {
        violations.extend(configured_directory_violation(ConfiguredDirectoryRequest {
            repo_root,
            source_roots: &source_roots,
            configured: path,
            kind: "role",
            require_role_name: true,
        }));
    }
    for path in &config.intentional_layout_paths {
        violations.extend(configured_directory_violation(ConfiguredDirectoryRequest {
            repo_root,
            source_roots: &source_roots,
            configured: path,
            kind: "intentional layout",
            require_role_name: false,
        }));
    }
    violations.extend(closed_inventory_violations(
        repo_root,
        &source_roots,
        config,
    ));
    violations
}

fn configured_directory_violation(
    request: ConfiguredDirectoryRequest<'_>,
) -> Vec<models::Violation> {
    let ConfiguredDirectoryRequest {
        repo_root,
        source_roots,
        configured,
        kind,
        require_role_name,
    } = request;
    let path = repo_root.join(configured);
    let canonical = path.canonicalize();
    let inside_source = canonical.as_ref().is_ok_and(|path| {
        path == &repo_root.join(configured)
            && source_roots.iter().any(|root| {
                path.starts_with(root) && (!kind.starts_with("intentional") || path != root)
            })
    });
    let role_name = path.file_name().and_then(|name| name.to_str());
    let recognized_role = role_name.is_some_and(|name| {
        path.is_dir() && constants::CONTAINER_DIRECTORY_NAMES.contains(&name)
            || path.is_file() && constants::ROLE_FILE_NAMES.contains(&name)
    });
    let valid_target = path.is_dir() && !require_role_name || recognized_role;
    if inside_source && valid_target {
        return Vec::new();
    }
    vec![models::Violation::new(models::ViolationRequest {
        code: "RSL305",
        path: Path::new(configured),
        line: None,
        message: format!("configured repository {kind} path is not a valid source path"),
        remediation: "declare an existing repository-relative role file or directory beneath one workspace crate's src/ tree",
    })]
}

fn closed_inventory_violations(
    repo_root: &Path,
    source_roots: &[PathBuf],
    config: &models::RepositoryPolicyConfig,
) -> Vec<models::Violation> {
    if config.domain_paths.is_empty() && config.role_paths.is_empty() {
        return Vec::new();
    }
    let intentional = config
        .intentional_layout_paths
        .iter()
        .map(|path| repo_root.join(path))
        .collect::<Vec<_>>();
    let mut roles: BTreeSet<String> = BTreeSet::new();
    let mut domains: BTreeSet<String> = BTreeSet::new();
    for source_root in source_roots {
        for entry in walkdir::WalkDir::new(source_root)
            .follow_links(false)
            .into_iter()
            .filter_map(Result::ok)
        {
            let path = entry.path();
            if !entry.file_type().is_file()
                || path.extension().and_then(|suffix| suffix.to_str())
                    != Some(constants::RUST_SUFFIX)
                || intentional.iter().any(|root| path.starts_with(root))
            {
                continue;
            }
            if let Ok(inside_source) = path.strip_prefix(source_root) {
                let mut components = inside_source.components();
                if let Some(first) = components.next() {
                    let name = first.as_os_str().to_string_lossy();
                    if components.next().is_some()
                        && !constants::CONTAINER_DIRECTORY_NAMES.contains(&name.as_ref())
                        && name != constants::TESTS_DIRECTORY
                        && name != constants::BIN_DIRECTORY
                    {
                        let domain = source_root.join(name.as_ref());
                        domains.insert(display_path(
                            domain.strip_prefix(repo_root).unwrap_or(&domain),
                        ));
                    }
                }
            }
            let file_name = path.file_name().and_then(|name| name.to_str());
            if file_name.is_some_and(|name| constants::ROLE_FILE_NAMES.contains(&name)) {
                roles.insert(display_path(path.strip_prefix(repo_root).unwrap_or(path)));
            }
            let mut ancestor = path.parent();
            while let Some(directory) = ancestor {
                if directory == source_root {
                    break;
                }
                let name = directory.file_name().and_then(|name| name.to_str());
                if name.is_some_and(|name| constants::CONTAINER_DIRECTORY_NAMES.contains(&name)) {
                    roles.insert(display_path(
                        directory.strip_prefix(repo_root).unwrap_or(directory),
                    ));
                }
                ancestor = directory.parent();
            }
        }
    }
    let configured_domains = config.domain_paths.iter().cloned().collect::<BTreeSet<_>>();
    let configured_roles = config.role_paths.iter().cloned().collect::<BTreeSet<_>>();
    let mut violations: Vec<models::Violation> = Vec::new();
    if !config.domain_paths.is_empty() {
        for undeclared in domains.difference(&configured_domains) {
            violations.push(inventory_violation(undeclared, "domain", false));
        }
        for stale in configured_domains.difference(&domains) {
            violations.push(inventory_violation(stale, "domain", true));
        }
    }
    if !config.role_paths.is_empty() {
        for undeclared in roles.difference(&configured_roles) {
            violations.push(inventory_violation(undeclared, "role", false));
        }
        for stale in configured_roles.difference(&roles) {
            violations.push(inventory_violation(stale, "role", true));
        }
    }
    if !configured_domains.is_empty() {
        for role in &configured_roles {
            if !configured_domains
                .iter()
                .any(|domain| role.starts_with(&format!("{domain}/")))
            {
                violations.push(models::Violation::new(models::ViolationRequest {
                    code: "RSL305",
                    path: Path::new(role),
                    line: None,
                    message: "configured repository role path is not owned by a declared domain",
                    remediation: "declare the role's owning domain or remove the role path",
                }));
            }
        }
    }
    violations
}

fn inventory_violation(path: &str, kind: &str, stale: bool) -> models::Violation {
    models::Violation::new(models::ViolationRequest {
        code: "RSL305",
        path: Path::new(path),
        line: None,
        message: if stale {
            format!("configured repository {kind} path contains no matching Rust structure")
        } else {
            format!("workspace {kind} path is not declared by repository policy")
        },
        remediation: if stale {
            format!("remove {path} from repository.{kind}-paths or restore its Rust structure")
        } else {
            format!("add {path} to repository.{kind}-paths or remove the structural path")
        },
    })
}

fn display_path(path: &Path) -> String {
    path.components()
        .map(|component| component.as_os_str().to_string_lossy())
        .collect::<Vec<_>>()
        .join("/")
}
