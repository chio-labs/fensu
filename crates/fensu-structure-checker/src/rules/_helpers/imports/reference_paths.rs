//! Collect canonical Rust paths from syntax and string-valued attributes.

use std::collections::BTreeSet;

use syn::spanned::Spanned;
use syn::visit::Visit;

const CRATE_ROOT: &str = "crate";
const PATH_SEPARATOR: &str = "::";
const SELF_ROOT: &str = "self";
const SUPER_ROOT: &str = "super";

pub(crate) fn collect(
    syntax: &syn::File,
    source: &str,
    package: &str,
) -> Vec<(Vec<String>, usize)> {
    let mut visitor = ReferenceVisitor::default();
    visitor.visit_file(syntax);
    collect_string_paths(source, &mut visitor);
    for (target, _) in &mut visitor.references {
        normalize_root(target, package);
    }
    visitor.references
}

pub(crate) fn module_path(package: &str, relative: &str) -> Vec<String> {
    let Some((_, inside)) = relative.split_once("/src/") else {
        return vec![package.to_owned()];
    };
    let mut parts = inside.split('/').map(str::to_owned).collect::<Vec<_>>();
    let Some(file) = parts.pop() else {
        return vec![package.to_owned()];
    };
    if !matches!(file.as_str(), "lib.rs" | "main.rs" | "mod.rs") {
        parts.push(file.trim_end_matches(".rs").to_owned());
    }
    let mut module = vec![package.to_owned()];
    module.extend(parts);
    module
}

fn collect_string_paths(source: &str, visitor: &mut ReferenceVisitor) {
    for (line_index, line) in source.lines().enumerate() {
        for value in line.split('"').skip(1).step_by(2) {
            if value.starts_with(&format!("{CRATE_ROOT}{PATH_SEPARATOR}")) {
                visitor.push(
                    value.split(PATH_SEPARATOR).map(str::to_owned).collect(),
                    line_index + 1,
                );
            }
        }
    }
}

fn normalize_root(target: &mut [String], package: &str) {
    if target.first().is_some_and(|root| root == CRATE_ROOT) {
        target[0] = package.to_owned();
    }
}

#[derive(Default)]
struct ReferenceVisitor {
    references: Vec<(Vec<String>, usize)>,
    seen: BTreeSet<(Vec<String>, usize)>,
}

impl ReferenceVisitor {
    fn push(&mut self, target: Vec<String>, line: usize) {
        if target.is_empty()
            || target
                .first()
                .is_some_and(|root| matches!(root.as_str(), SELF_ROOT | SUPER_ROOT))
        {
            return;
        }
        if self.seen.insert((target.clone(), line)) {
            self.references.push((target, line));
        }
    }
}

impl<'ast> Visit<'ast> for ReferenceVisitor {
    fn visit_item_use(&mut self, node: &'ast syn::ItemUse) {
        let mut paths = Vec::new();
        flatten_use_tree(&node.tree, &mut Vec::new(), &mut paths);
        for target in paths {
            self.push(target, node.use_token.span.start().line);
        }
    }

    fn visit_path(&mut self, node: &'ast syn::Path) {
        let target = node
            .segments
            .iter()
            .map(|segment| segment.ident.to_string())
            .collect::<Vec<_>>();
        self.push(target, node.span().start().line);
        syn::visit::visit_path(self, node);
    }
}

fn flatten_use_tree(tree: &syn::UseTree, prefix: &mut Vec<String>, out: &mut Vec<Vec<String>>) {
    match tree {
        syn::UseTree::Path(path) => {
            prefix.push(path.ident.to_string());
            flatten_use_tree(&path.tree, prefix, out);
            prefix.pop();
        }
        syn::UseTree::Name(name) => {
            let mut path = prefix.clone();
            if name.ident != SELF_ROOT {
                path.push(name.ident.to_string());
            }
            out.push(path);
        }
        syn::UseTree::Rename(rename) => {
            let mut path = prefix.clone();
            path.push(rename.ident.to_string());
            out.push(path);
        }
        syn::UseTree::Glob(_) => out.push(prefix.clone()),
        syn::UseTree::Group(group) => {
            for item in &group.items {
                flatten_use_tree(item, prefix, out);
            }
        }
    }
}
