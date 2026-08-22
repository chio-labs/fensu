//! Layer rules: import discipline and crate dependency direction.

use std::fs;
use std::path;

use syn::visit::Visit;

use crate::constants;
use crate::models;
use crate::rules::_helpers::imports::reference_paths;
use crate::rules::_helpers::sources::scanning;

/// Check every use declaration in one file for layer violations.
pub(crate) fn check_uses(
    file: &models::SourceFile,
    syntax: &syn::File,
    library_source: bool,
    raw_parser_boundary: &models::RawParserBoundaryConfig,
) -> Vec<models::Violation> {
    let mut visitor = UseVisitor {
        file,
        library_source,
        raw_parser_boundary,
        violations: Vec::new(),
    };
    visitor.visit_file(syntax);
    visitor.violations
}

/// Check one crate manifest for workspace and dependency policy.
pub(crate) fn check_manifest(
    repo_root: &path::Path,
    crate_dir: &path::Path,
    config: &models::CheckerConfig,
) -> Vec<models::Violation> {
    let manifest_path = crate_dir.join(constants::CARGO_MANIFEST_FILE);
    let source = match fs::read_to_string(&manifest_path) {
        Ok(value) => value,
        Err(error) => {
            return vec![scanning::manifest_setup_violation(
                repo_root,
                &manifest_path,
                format!("cannot read crate manifest: {error}"),
            )];
        }
    };
    let manifest = match toml::from_str::<toml::Value>(&source) {
        Ok(value) => value,
        Err(error) => {
            return vec![scanning::manifest_setup_violation(
                repo_root,
                &manifest_path,
                format!("cannot parse crate manifest: {error}"),
            )];
        }
    };
    let relative = manifest_path
        .strip_prefix(repo_root)
        .unwrap_or(&manifest_path);
    let Some(crate_name) = manifest
        .get(constants::PACKAGE_KEY)
        .and_then(|value| value.get(constants::NAME_KEY))
        .and_then(toml::Value::as_str)
    else {
        return vec![scanning::manifest_setup_violation(
            repo_root,
            &manifest_path,
            "crate manifest declares no package name",
        )];
    };
    let mut violations = crate_manifest_violations(relative, &manifest);
    if crate_name != config.tooling.package {
        violations.extend(tooling_dependency_violations(
            relative,
            &manifest,
            &config.tooling.runtime_forbidden_packages,
        ));
    }
    violations
}

fn crate_manifest_violations(
    relative: &path::Path,
    manifest: &toml::Value,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let inherits_lints = manifest
        .get(constants::LINTS_KEY)
        .and_then(|value| value.get(constants::WORKSPACE_KEY))
        .and_then(toml::Value::as_bool)
        == Some(true);
    if !inherits_lints {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSL302",
            path: relative,
            line: None,
            message: "crate does not inherit the workspace lint policy",
            remediation: "add [lints] workspace = true to the crate manifest",
        }));
    }
    violations.extend(dependency_policy_violations(relative, manifest));
    violations
}

fn dependency_policy_violations(
    relative: &path::Path,
    manifest: &toml::Value,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for table in dependency_tables(manifest) {
        for (name, specification) in table {
            let inherits = specification
                .get(constants::WORKSPACE_KEY)
                .and_then(toml::Value::as_bool)
                == Some(true);
            if !inherits {
                violations.push(models::Violation::new(models::ViolationRequest {
code: "RSL307",
path: relative,
line: None,
message: format!("dependency {name} does not inherit workspace policy"),
remediation: "declare the dependency under [workspace.dependencies] and use workspace = true",
}));
            }
            violations.extend(dependency_declaration_violations(
                relative,
                name,
                specification,
            ));
        }
    }
    violations
}

pub(crate) fn workspace_dependency_policy_violations(
    relative: &path::Path,
    manifest: &toml::Value,
) -> Vec<models::Violation> {
    let Some(dependencies) = manifest
        .get(constants::WORKSPACE_KEY)
        .and_then(|value| value.get(constants::DEPENDENCIES_KEY))
        .and_then(toml::Value::as_table)
    else {
        return Vec::new();
    };
    let mut violations: Vec<models::Violation> = Vec::new();
    for (name, specification) in dependencies {
        violations.extend(dependency_declaration_violations(
            relative,
            name,
            specification,
        ));
    }
    violations
}

fn dependency_declaration_violations(
    relative: &path::Path,
    name: &str,
    specification: &toml::Value,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    if specification_version(specification) == Some(constants::WILDCARD_VERSION) {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSL304",
            path: relative,
            line: None,
            message: format!("dependency {name} uses a wildcard version"),
            remediation: "pin the dependency in [workspace.dependencies]",
        }));
    }
    let unpinned_git = specification.get(constants::GIT_KEY).is_some()
        && specification.get(constants::REV_KEY).is_none();
    if unpinned_git {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSL305",
            path: relative,
            line: None,
            message: format!("Git dependency {name} is not pinned to a revision"),
            remediation: "set an immutable rev in the workspace dependency declaration",
        }));
    }
    let escaping_path = specification
        .get(constants::PATH_KEY)
        .and_then(toml::Value::as_str)
        .is_some_and(|value| {
            path::Path::new(value).components().any(|component| {
                matches!(
                    component,
                    path::Component::ParentDir | path::Component::RootDir
                )
            })
        });
    if escaping_path {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSL306",
            path: relative,
            line: None,
            message: format!("path dependency {name} escapes its manifest directory"),
            remediation: "own workspace paths at the repository root without parent traversal",
        }));
    }
    violations
}

fn dependency_tables(manifest: &toml::Value) -> Vec<&toml::map::Map<String, toml::Value>> {
    let mut tables: Vec<&toml::map::Map<String, toml::Value>> = constants::DEPENDENCY_TABLE_NAMES
        .iter()
        .filter_map(|name| manifest.get(*name).and_then(toml::Value::as_table))
        .collect();
    if let Some(targets) = manifest
        .get(constants::TARGET_KEY)
        .and_then(toml::Value::as_table)
    {
        for target in targets.values().filter_map(toml::Value::as_table) {
            for name in constants::DEPENDENCY_TABLE_NAMES {
                if let Some(table) = target.get(*name).and_then(toml::Value::as_table) {
                    tables.push(table);
                }
            }
        }
    }
    tables
}

fn tooling_dependency_violations(
    relative: &path::Path,
    manifest: &toml::Value,
    forbidden_packages: &[String],
) -> Vec<models::Violation> {
    for table in dependency_tables(manifest) {
        for (name, specification) in table {
            if let Some(tooling_package) =
                forbidden_tooling_package(name, specification, forbidden_packages)
            {
                return vec![models::Violation::new(models::ViolationRequest {
                    code: "RSL301",
                    path: relative,
                    line: None,
                    message: format!("crate depends on {tooling_package}"),
                    remediation:
                        "the structure checker is tooling; runtime crates must not depend on it",
                })];
            }
        }
    }
    Vec::new()
}

fn forbidden_tooling_package<'a>(
    dependency_name: &str,
    specification: &toml::Value,
    forbidden_packages: &'a [String],
) -> Option<&'a str> {
    let package = specification
        .get(constants::PACKAGE_KEY)
        .and_then(toml::Value::as_str);
    forbidden_packages
        .iter()
        .find(|forbidden| {
            dependency_name == forbidden.as_str() || package == Some(forbidden.as_str())
        })
        .map(String::as_str)
}

fn specification_version(specification: &toml::Value) -> Option<&str> {
    specification.as_str().or_else(|| {
        specification
            .get(constants::VERSION_KEY)
            .and_then(toml::Value::as_str)
    })
}

struct UseVisitor<'files> {
    file: &'files models::SourceFile,
    library_source: bool,
    raw_parser_boundary: &'files models::RawParserBoundaryConfig,
    violations: Vec<models::Violation>,
}

impl<'ast, 'files> Visit<'ast> for UseVisitor<'files> {
    fn visit_item_use(&mut self, node: &'ast syn::ItemUse) {
        let line = node.use_token.span.start().line;
        if self.library_source && self.file.has_directory(constants::RULES_DIRECTORY) {
            self.violations.extend(raw_parser_access_violations(
                self.file,
                &node.tree,
                line,
                self.raw_parser_boundary,
            ));
        }
        if let syn::UseTree::Path(use_path) = &node.tree {
            let root = use_path.ident.to_string();
            if root == constants::SELF_MODULE || root == constants::SUPER_MODULE {
                self.violations
                    .push(models::Violation::new(models::ViolationRequest {
                        code: "RSL001",
                        path: self.file.relative_path(),
                        line: Some(line),
                        message: format!("use path starts with {root}"),
                        remediation: "import through crate::, std::, or an external crate name",
                    }));
            }
        }
        if contains_glob(&node.tree) {
            self.violations
                .push(models::Violation::new(models::ViolationRequest {
                    code: "RSL002",
                    path: self.file.relative_path(),
                    line: Some(line),
                    message: "wildcard import hides the names a module depends on",
                    remediation: "import each required name explicitly",
                }));
        }
        if self.library_source {
            self.violations
                .extend(helper_boundary_violations(self.file, node, line));
        }
        syn::visit::visit_item_use(self, node);
    }
}

fn raw_parser_access_violations(
    file: &models::SourceFile,
    tree: &syn::UseTree,
    line: usize,
    config: &models::RawParserBoundaryConfig,
) -> Vec<models::Violation> {
    reference_paths::use_paths(tree)
        .into_iter()
        .filter_map(|path| path.first().cloned())
        .filter(|root| config.packages.contains(root))
        .map(|root| {
            models::Violation::new(models::ViolationRequest {
                code: "RSL102",
                path: file.relative_path(),
                line: Some(line),
                message: format!("native rule module imports raw parser crate {root}"),
                remediation: &config.remediation,
            })
        })
        .collect()
}

fn helper_boundary_violations(
    file: &models::SourceFile,
    node: &syn::ItemUse,
    line: usize,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let paths = reference_paths::use_paths(&node.tree);
    for segments in &paths {
        if segments.first().map(String::as_str) != Some("crate") {
            continue;
        }
        let Some(position) = segments
            .iter()
            .position(|segment| segment == constants::HELPERS_DIRECTORY)
        else {
            continue;
        };
        if position < constants::MIN_DOMAIN_SEGMENTS {
            continue;
        }
        let owner = segments[1..position].join("/");
        let inside = file
            .relative
            .split_once("/src/")
            .map(|(_, rest)| rest)
            .unwrap_or_default();
        if inside.starts_with(&format!("{owner}/")) {
            continue;
        }
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSL101",
            path: file.relative_path(),
            line: Some(line),
            message: format!("imports helper internals of the {owner} domain"),
            remediation: "use the owning domain's entry modules or role files instead",
        }));
    }
    violations
}

fn contains_glob(tree: &syn::UseTree) -> bool {
    match tree {
        syn::UseTree::Glob(_) => true,
        syn::UseTree::Path(use_path) => contains_glob(&use_path.tree),
        syn::UseTree::Group(group) => group.items.iter().any(contains_glob),
        _ => false,
    }
}
