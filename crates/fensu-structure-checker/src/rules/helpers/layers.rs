//! Layer rules: import discipline and crate dependency direction.

use std::fs;
use std::path;

use syn::visit::Visit;

use crate::constants;
use crate::models;
use crate::rules::helpers::scanning;

/// Check every use declaration in one file for layer violations.
pub(crate) fn check_uses(
    file: &models::SourceFile,
    syntax: &syn::File,
    library_source: bool,
) -> Vec<models::Violation> {
    let mut visitor = UseVisitor {
        file,
        library_source,
        violations: Vec::new(),
    };
    visitor.visit_file(syntax);
    visitor.violations
}

/// Check one crate manifest for workspace and dependency policy.
pub(crate) fn check_manifest(
    repo_root: &path::Path,
    crate_dir: &path::Path,
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
    if crate_name != constants::TOOLING_CRATE_NAME {
        violations.extend(tooling_dependency_violations(relative, &manifest));
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
        violations.push(models::Violation::new(
            "RSL302",
            relative,
            None,
            "crate does not inherit the workspace lint policy",
            "add [lints] workspace = true to the crate manifest",
        ));
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
                violations.push(models::Violation::new(
                    "RSL307",
                    relative,
                    None,
                    format!("dependency {name} does not inherit workspace policy"),
                    "declare the dependency under [workspace.dependencies] and use workspace = true",
                ));
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
        violations.push(models::Violation::new(
            "RSL304",
            relative,
            None,
            format!("dependency {name} uses a wildcard version"),
            "pin the dependency in [workspace.dependencies]",
        ));
    }
    let unpinned_git = specification.get(constants::GIT_KEY).is_some()
        && specification.get(constants::REV_KEY).is_none();
    if unpinned_git {
        violations.push(models::Violation::new(
            "RSL305",
            relative,
            None,
            format!("Git dependency {name} is not pinned to a revision"),
            "set an immutable rev in the workspace dependency declaration",
        ));
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
        violations.push(models::Violation::new(
            "RSL306",
            relative,
            None,
            format!("path dependency {name} escapes its manifest directory"),
            "own workspace paths at the repository root without parent traversal",
        ));
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
) -> Vec<models::Violation> {
    for table in dependency_tables(manifest) {
        let contains_tooling = table.iter().any(|(name, specification)| {
            let package = specification
                .get(constants::PACKAGE_KEY)
                .and_then(toml::Value::as_str);
            name == constants::TOOLING_CRATE_NAME || package == Some(constants::TOOLING_CRATE_NAME)
        });
        if contains_tooling {
            return vec![models::Violation::new(
                "RSL301",
                relative,
                None,
                format!("crate depends on {}", constants::TOOLING_CRATE_NAME),
                "the structure checker is tooling; runtime crates must not depend on it",
            )];
        }
    }
    Vec::new()
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
    violations: Vec<models::Violation>,
}

impl<'ast, 'files> Visit<'ast> for UseVisitor<'files> {
    fn visit_item_use(&mut self, node: &'ast syn::ItemUse) {
        let line = node.use_token.span.start().line;
        if self.library_source && self.file.has_directory(constants::RULES_DIRECTORY) {
            self.violations
                .extend(raw_parser_access_violations(self.file, &node.tree, line));
        }
        if let syn::UseTree::Path(use_path) = &node.tree {
            let root = use_path.ident.to_string();
            if root == constants::SELF_MODULE || root == constants::SUPER_MODULE {
                self.violations.push(models::Violation::new(
                    "RSL001",
                    self.file.relative_path(),
                    Some(line),
                    format!("use path starts with {root}"),
                    "import through crate::, std::, or an external crate name",
                ));
            }
        }
        if contains_glob(&node.tree) {
            self.violations.push(models::Violation::new(
                "RSL002",
                self.file.relative_path(),
                Some(line),
                "wildcard import hides the names a module depends on",
                "import each required name explicitly",
            ));
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
) -> Vec<models::Violation> {
    let mut paths: Vec<Vec<String>> = Vec::new();
    flatten_use_tree(tree, &mut Vec::new(), &mut paths);
    paths
        .into_iter()
        .filter_map(|path| path.first().cloned())
        .filter(|root| constants::RAW_PARSER_CRATES.contains(&root.as_str()))
        .map(|root| {
            models::Violation::new(
                "RSL102",
                file.relative_path(),
                Some(line),
                format!("native rule module imports raw parser crate {root}"),
                "consume shared fensu-facts row models instead of parser or AST types",
            )
        })
        .collect()
}

fn helper_boundary_violations(
    file: &models::SourceFile,
    node: &syn::ItemUse,
    line: usize,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let mut paths: Vec<Vec<String>> = Vec::new();
    flatten_use_tree(&node.tree, &mut Vec::new(), &mut paths);
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
        violations.push(models::Violation::new(
            "RSL101",
            file.relative_path(),
            Some(line),
            format!("imports helper internals of the {owner} domain"),
            "use the owning domain's entry modules or role files instead",
        ));
    }
    violations
}

fn flatten_use_tree(tree: &syn::UseTree, prefix: &mut Vec<String>, out: &mut Vec<Vec<String>>) {
    match tree {
        syn::UseTree::Path(use_path) => {
            prefix.push(use_path.ident.to_string());
            flatten_use_tree(&use_path.tree, prefix, out);
            let _ = prefix.pop();
        }
        syn::UseTree::Name(name) => {
            prefix.push(name.ident.to_string());
            out.push(prefix.to_vec());
            let _ = prefix.pop();
        }
        syn::UseTree::Rename(rename) => {
            prefix.push(rename.ident.to_string());
            out.push(prefix.to_vec());
            let _ = prefix.pop();
        }
        syn::UseTree::Glob(_) => out.push(prefix.to_vec()),
        syn::UseTree::Group(group) => {
            for item in &group.items {
                flatten_use_tree(item, prefix, out);
            }
        }
    }
}

fn contains_glob(tree: &syn::UseTree) -> bool {
    match tree {
        syn::UseTree::Glob(_) => true,
        syn::UseTree::Path(use_path) => contains_glob(&use_path.tree),
        syn::UseTree::Group(group) => group.items.iter().any(contains_glob),
        _ => false,
    }
}
