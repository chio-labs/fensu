//! Project-aware discarded-result policy for Rust `#[must_use]` functions.

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path;

use syn::spanned::Spanned;
use syn::visit::Visit;

use crate::constants;
use crate::models;
use crate::rules::_helpers::imports::reference_paths;
use crate::rules::_helpers::sources::scanning;

const CRATE_ROOT: &str = "crate";
const MUST_USE_ATTRIBUTE: &str = "must_use";

#[derive(Debug)]
struct CrateSources {
    package: String,
    files: Vec<models::SourceFile>,
}

#[derive(Debug)]
struct DiscardedCall {
    file: String,
    line: usize,
    target: Vec<String>,
}

pub(crate) fn check_workspace(
    repo_root: &path::Path,
    crate_directories: &[path::PathBuf],
) -> Vec<models::Violation> {
    let crates = crate_directories
        .iter()
        .filter_map(|crate_dir| crate_sources(repo_root, crate_dir))
        .collect::<Vec<_>>();
    let meaningful = crates
        .iter()
        .flat_map(must_use_functions)
        .collect::<BTreeSet<_>>();
    let mut violations = Vec::new();
    for crate_sources in &crates {
        for call in discarded_calls(crate_sources) {
            if meaningful.contains(&call.target) {
                violations.push(models::Violation::new(models::ViolationRequest {
                    code: "RSS101",
                    path: path::Path::new(&call.file),
                    line: Some(call.line),
                    message: format!(
                        "main orchestrator discards the meaningful result of {}",
                        call.target.join("::")
                    ),
                    remediation:
                        "assign, return, or explicitly discard the result with let _ = call(...) ",
                }));
            }
        }
    }
    violations
}

fn crate_sources(repo_root: &path::Path, crate_dir: &path::Path) -> Option<CrateSources> {
    let manifest = fs::read_to_string(crate_dir.join(constants::CARGO_MANIFEST_FILE)).ok()?;
    let document = toml::from_str::<toml::Value>(&manifest).ok()?;
    let package = document
        .get(constants::PACKAGE_KEY)?
        .get(constants::NAME_KEY)?
        .as_str()?
        .replace('-', "_");
    let scan = scanning::rust_files(repo_root, &crate_dir.join(constants::SOURCE_DIRECTORY));
    Some(CrateSources {
        package,
        files: scan.files,
    })
}

fn must_use_functions(crate_sources: &CrateSources) -> Vec<Vec<String>> {
    let mut functions = Vec::new();
    for file in &crate_sources.files {
        let Ok(syntax) = syn::parse_file(&file.source) else {
            continue;
        };
        let module = reference_paths::module_path(&crate_sources.package, &file.relative);
        for item in syntax.items {
            let syn::Item::Fn(function) = item else {
                continue;
            };
            if !function
                .attrs
                .iter()
                .any(|attribute| attribute.path().is_ident(MUST_USE_ATTRIBUTE))
            {
                continue;
            }
            let mut target = module.clone();
            target.push(function.sig.ident.to_string());
            functions.push(target);
        }
    }
    functions
}

fn discarded_calls(crate_sources: &CrateSources) -> Vec<DiscardedCall> {
    let mut calls = Vec::new();
    for file in &crate_sources.files {
        if !file.has_directory(constants::MAIN_DIRECTORY) || file.file_name() == constants::MOD_FILE
        {
            continue;
        }
        let Ok(syntax) = syn::parse_file(&file.source) else {
            continue;
        };
        let module = reference_paths::module_path(&crate_sources.package, &file.relative);
        let mut visitor = DiscardVisitor {
            package: &crate_sources.package,
            module: &module,
            file: &file.relative,
            imports: BTreeMap::new(),
            calls: &mut calls,
        };
        visitor.visit_file(&syntax);
    }
    calls
}

struct DiscardVisitor<'a> {
    package: &'a str,
    module: &'a [String],
    file: &'a str,
    imports: BTreeMap<String, Vec<String>>,
    calls: &'a mut Vec<DiscardedCall>,
}

impl Visit<'_> for DiscardVisitor<'_> {
    fn visit_item_use(&mut self, node: &syn::ItemUse) {
        for (bound, target) in collect_bindings(&node.tree) {
            let target = normalize_root(target, self.package);
            self.imports.insert(bound, target);
        }
    }

    fn visit_stmt(&mut self, node: &syn::Stmt) {
        let syn::Stmt::Expr(syn::Expr::Call(call), Some(_)) = node else {
            syn::visit::visit_stmt(self, node);
            return;
        };
        let syn::Expr::Path(function) = call.func.as_ref() else {
            syn::visit::visit_stmt(self, node);
            return;
        };
        let mut target = function
            .path
            .segments
            .iter()
            .map(|segment| segment.ident.to_string())
            .collect::<Vec<_>>();
        if target.len() == 1 {
            target = self.imports.get(&target[0]).cloned().unwrap_or_else(|| {
                let mut local = self.module.to_vec();
                local.push(target[0].clone());
                local
            });
        } else {
            target = normalize_root(target, self.package);
        }
        self.calls.push(DiscardedCall {
            file: self.file.to_owned(),
            line: call.span().start().line,
            target,
        });
        syn::visit::visit_stmt(self, node);
    }
}

fn normalize_root(mut target: Vec<String>, package: &str) -> Vec<String> {
    if target.first().is_some_and(|root| root == CRATE_ROOT) {
        target[0] = package.to_owned();
    }
    target
}

fn collect_bindings(tree: &syn::UseTree) -> Vec<(String, Vec<String>)> {
    let mut collector = BindingCollector {
        bindings: Vec::new(),
    };
    collector.collect(tree, Vec::new());
    collector.bindings
}

struct BindingCollector {
    bindings: Vec<(String, Vec<String>)>,
}

impl BindingCollector {
    fn collect(&mut self, tree: &syn::UseTree, prefix: Vec<String>) {
        match tree {
            syn::UseTree::Path(path) => {
                let mut child = prefix;
                child.push(path.ident.to_string());
                self.collect(&path.tree, child);
            }
            syn::UseTree::Name(name) => {
                let mut target = prefix;
                target.push(name.ident.to_string());
                self.bindings.push((name.ident.to_string(), target));
            }
            syn::UseTree::Rename(rename) => {
                let mut target = prefix;
                target.push(rename.ident.to_string());
                self.bindings.push((rename.rename.to_string(), target));
            }
            syn::UseTree::Group(group) => {
                for item in &group.items {
                    self.collect(item, prefix.clone());
                }
            }
            syn::UseTree::Glob(_) => {}
        }
    }
}
