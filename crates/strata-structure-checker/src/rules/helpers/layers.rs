//! Layer rules: import discipline and crate dependency direction.

use std::fs;
use std::path;

use syn::visit::Visit;

use crate::constants;
use crate::models;

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

/// Check one crate manifest for dependencies on the tooling crate.
pub(crate) fn check_manifest(
    repo_root: &path::Path,
    crate_dir: &path::Path,
) -> Vec<models::Violation> {
    let crate_name = crate_dir
        .file_name()
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default();
    if crate_name == constants::TOOLING_CRATE_NAME {
        return Vec::new();
    }
    let manifest_path = crate_dir.join("Cargo.toml");
    let manifest = fs::read_to_string(&manifest_path).unwrap_or_default();
    if !manifest.contains(constants::TOOLING_CRATE_NAME) {
        return Vec::new();
    }
    let relative = manifest_path
        .strip_prefix(repo_root)
        .unwrap_or(&manifest_path);
    vec![models::Violation::new(
        "RSL301",
        relative,
        None,
        format!("crate depends on {}", constants::TOOLING_CRATE_NAME),
        "the structure checker is tooling; runtime crates must not depend on it",
    )]
}

struct UseVisitor<'files> {
    file: &'files models::SourceFile,
    library_source: bool,
    violations: Vec<models::Violation>,
}

impl<'ast, 'files> Visit<'ast> for UseVisitor<'files> {
    fn visit_item_use(&mut self, node: &'ast syn::ItemUse) {
        let line = node.use_token.span.start().line;
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

fn helper_boundary_violations(
    file: &models::SourceFile,
    node: &syn::ItemUse,
    line: usize,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let mut paths: Vec<Vec<String>> = Vec::new();
    flatten_use_tree(&node.tree, Vec::new(), &mut paths);
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

fn flatten_use_tree(tree: &syn::UseTree, prefix: Vec<String>, out: &mut Vec<Vec<String>>) {
    match tree {
        syn::UseTree::Path(use_path) => {
            let mut extended = prefix.clone();
            extended.push(use_path.ident.to_string());
            flatten_use_tree(&use_path.tree, extended, out);
        }
        syn::UseTree::Name(name) => {
            let mut extended = prefix.clone();
            extended.push(name.ident.to_string());
            out.push(extended);
        }
        syn::UseTree::Rename(rename) => {
            let mut extended = prefix.clone();
            extended.push(rename.ident.to_string());
            out.push(extended);
        }
        syn::UseTree::Glob(_) => out.push(prefix),
        syn::UseTree::Group(group) => {
            for item in &group.items {
                flatten_use_tree(item, prefix.clone(), out);
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
