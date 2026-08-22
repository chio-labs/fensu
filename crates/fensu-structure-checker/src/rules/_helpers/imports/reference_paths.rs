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
    visitor.collect_string_paths(source);
    visitor
        .references
        .into_iter()
        .map(|(target, line)| (normalize_root(target, package), line))
        .collect()
}

pub(crate) fn module_path(package: &str, file: &crate::models::SourceFile) -> Vec<String> {
    let mut parts = file
        .source_relative
        .split('/')
        .map(str::to_owned)
        .collect::<Vec<_>>();
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

fn normalize_root(mut target: Vec<String>, package: &str) -> Vec<String> {
    if target.first().is_some_and(|root| root == CRATE_ROOT) {
        target[0] = package.to_owned();
    }
    target
}

pub(crate) fn use_paths(tree: &syn::UseTree) -> Vec<Vec<String>> {
    let mut collector = UsePathCollector { paths: Vec::new() };
    collector.collect(tree, Vec::new());
    collector.paths
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

    fn collect_string_paths(&mut self, source: &str) {
        for (line_index, line) in source.lines().enumerate() {
            for value in line.split('"').skip(1).step_by(2) {
                if value.starts_with(&format!("{CRATE_ROOT}{PATH_SEPARATOR}")) {
                    self.push(
                        value.split(PATH_SEPARATOR).map(str::to_owned).collect(),
                        line_index + 1,
                    );
                }
            }
        }
    }
}

impl<'ast> Visit<'ast> for ReferenceVisitor {
    fn visit_item_use(&mut self, node: &'ast syn::ItemUse) {
        for target in use_paths(&node.tree) {
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

struct UsePathCollector {
    paths: Vec<Vec<String>>,
}

impl UsePathCollector {
    fn collect(&mut self, tree: &syn::UseTree, prefix: Vec<String>) {
        match tree {
            syn::UseTree::Path(path) => {
                let mut child = prefix;
                child.push(path.ident.to_string());
                self.collect(&path.tree, child);
            }
            syn::UseTree::Name(name) => {
                let mut path = prefix;
                if name.ident != SELF_ROOT {
                    path.push(name.ident.to_string());
                }
                self.paths.push(path);
            }
            syn::UseTree::Rename(rename) => {
                let mut path = prefix;
                path.push(rename.ident.to_string());
                self.paths.push(path);
            }
            syn::UseTree::Glob(_) => self.paths.push(prefix),
            syn::UseTree::Group(group) => {
                for item in &group.items {
                    self.collect(item, prefix.clone());
                }
            }
        }
    }
}
