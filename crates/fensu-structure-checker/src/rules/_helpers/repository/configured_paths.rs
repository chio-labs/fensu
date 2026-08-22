//! Validate configured crate identities and structural paths against a workspace.

use std::path::Path;

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
        .map(|workspace_crate| workspace_crate.directory.join(constants::SOURCE_DIRECTORY))
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
    let inside_source = source_roots.iter().any(|root| path.starts_with(root));
    let role_name = path.file_name().and_then(|name| name.to_str());
    let recognized_role = role_name.is_some_and(|name| {
        constants::CONTAINER_DIRECTORY_NAMES.contains(&name)
            || constants::ROLE_FILE_NAMES
                .iter()
                .any(|file| file.trim_end_matches(".rs") == name)
    });
    if path.is_dir() && inside_source && (!require_role_name || recognized_role) {
        return Vec::new();
    }
    vec![models::Violation::new(models::ViolationRequest {
        code: "RSL305",
        path: Path::new(configured),
        line: None,
        message: format!("configured repository {kind} path is not a valid source directory"),
        remediation: "declare an existing repository-relative directory beneath one workspace crate's src/ tree",
    })]
}
