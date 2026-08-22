//! Workspace visibility rules over module declarations and cross-file references.

use std::collections::BTreeMap;
use std::path;

use crate::constants;
use crate::models;
use crate::rules::_helpers::imports::reference_paths;
use crate::rules::_helpers::sources::scanning;

const CRATE_ROOT: &str = "crate";
const TEST_ONLY_CRATE_ATTRIBUTE: &str = "#![cfg(test)]";
const PYMODULE_ATTRIBUTE: &str = "pymodule";

#[derive(Clone, Debug)]
struct Reference {
    source_package: String,
    source_domain: Option<String>,
    source_file: String,
    target: Vec<String>,
    line: usize,
}

#[derive(Clone, Debug)]
struct Entry {
    domain: Option<String>,
    file: String,
    module: Vec<String>,
    public_to_crate: bool,
    externally_declared: bool,
}

#[derive(Clone, Debug)]
struct HelperType {
    file: String,
    symbol: Vec<String>,
}

#[derive(Debug)]
struct CrateSources {
    package: String,
    files: Vec<models::SourceFile>,
}

#[derive(Debug, Default)]
struct VisibilityIndex {
    references: Vec<Reference>,
    entries: Vec<Entry>,
    helper_types: Vec<HelperType>,
    violations: Vec<models::Violation>,
}

pub(crate) fn check_workspace(
    repo_root: &path::Path,
    workspace_crates: &[models::WorkspaceCrate],
) -> Vec<models::Violation> {
    let crates = workspace_crates
        .iter()
        .filter_map(|workspace_crate| crate_sources(repo_root, workspace_crate))
        .collect::<Vec<_>>();
    let mut index = VisibilityIndex::default();
    for crate_sources in &crates {
        index.collect_crate(crate_sources);
    }
    index.violations.extend(private_entry_import_violations(
        &index.references,
        &index.entries,
    ));
    index.violations.extend(unused_public_entry_violations(
        &index.references,
        &index.entries,
    ));
    index.violations.extend(private_helper_type_violations(
        &index.references,
        &index.helper_types,
    ));
    index
        .violations
        .sort_by(|left, right| left.sort_key().cmp(&right.sort_key()));
    index
        .violations
        .dedup_by(|left, right| left.sort_key() == right.sort_key());
    index.violations
}

fn crate_sources(
    repo_root: &path::Path,
    workspace_crate: &models::WorkspaceCrate,
) -> Option<CrateSources> {
    let package = workspace_crate.package_name.as_ref()?.replace('-', "_");
    let scan = scanning::rust_target_files(repo_root, workspace_crate, false);
    Some(CrateSources {
        package,
        files: scan.files,
    })
}

impl VisibilityIndex {
    fn collect_crate(&mut self, crate_sources: &CrateSources) {
        let module_visibility = module_visibility(crate_sources);
        for file in &crate_sources.files {
            if is_test_source(file) {
                continue;
            }
            let Ok(syntax) = syn::parse_file(&file.source) else {
                continue;
            };
            let current_module = reference_paths::module_path(&crate_sources.package, file);
            let source_domain = current_module.get(1).cloned();
            for (target, line) in
                reference_paths::collect(&syntax, &file.source, &crate_sources.package)
            {
                if targets_bare_crate_surface(&target, &crate_sources.package, &module_visibility)
                    && !is_crate_root(file)
                {
                    self.violations
                        .push(models::Violation::new(models::ViolationRequest {
                            code: "RSL103",
                            path: file.relative_path(),
                            line: Some(line),
                            message: "internal module imports from the crate's bare public surface",
                            remediation:
                                "import from the concrete owning module below the crate root",
                        }));
                }
                self.references.push(Reference {
                    source_package: crate_sources.package.clone(),
                    source_domain: source_domain.clone(),
                    source_file: file.relative.clone(),
                    target,
                    line,
                });
            }
            if let Some(entry) = collect_entry(file, &current_module, &module_visibility, &syntax) {
                self.entries.push(entry);
            }
            self.helper_types
                .extend(collect_helper_types(file, &current_module, &syntax));
        }
    }
}

fn module_visibility(crate_sources: &CrateSources) -> BTreeMap<Vec<String>, bool> {
    let mut result: BTreeMap<Vec<String>, bool> = BTreeMap::new();
    for file in &crate_sources.files {
        let Ok(syntax) = syn::parse_file(&file.source) else {
            continue;
        };
        let parent = reference_paths::module_path(&crate_sources.package, file);
        for item in syntax.items {
            let syn::Item::Mod(item_mod) = item else {
                continue;
            };
            let mut child = parent.clone();
            child.push(item_mod.ident.to_string());
            result.insert(child, public_to_crate(&item_mod.vis));
        }
    }
    result
}

fn collect_entry(
    file: &models::SourceFile,
    module: &[String],
    visibility: &BTreeMap<Vec<String>, bool>,
    syntax: &syn::File,
) -> Option<Entry> {
    if !file.has_directory(constants::MAIN_DIRECTORY)
        || file.file_name() == constants::MOD_FILE
        || file.file_name() == constants::INLINE_TEST_HARNESS_FILE
    {
        return None;
    }
    let public_to_crate = visibility.get(module).copied()?;
    Some(Entry {
        domain: module.get(1).cloned(),
        file: file.relative.clone(),
        module: module.to_vec(),
        public_to_crate,
        externally_declared: syntax.items.iter().any(externally_declared_item),
    })
}

fn externally_declared_item(item: &syn::Item) -> bool {
    let syn::Item::Fn(function) = item else {
        return false;
    };
    function
        .attrs
        .iter()
        .any(|attribute| attribute.path().is_ident(PYMODULE_ATTRIBUTE))
}

fn collect_helper_types(
    file: &models::SourceFile,
    module: &[String],
    syntax: &syn::File,
) -> Vec<HelperType> {
    if !file.has_directory(constants::HELPERS_DIRECTORY) {
        return Vec::new();
    }
    let mut helper_types: Vec<HelperType> = Vec::new();
    for item in &syntax.items {
        let declaration = match item {
            syn::Item::Enum(inner) => Some((&inner.ident, &inner.vis)),
            syn::Item::Struct(inner) => Some((&inner.ident, &inner.vis)),
            syn::Item::Trait(inner) => Some((&inner.ident, &inner.vis)),
            syn::Item::Type(inner) => Some((&inner.ident, &inner.vis)),
            _ => None,
        };
        let Some((identifier, visibility)) = declaration else {
            continue;
        };
        if public_to_crate(visibility) {
            continue;
        }
        let mut symbol = module.to_vec();
        symbol.push(identifier.to_string());
        helper_types.push(HelperType {
            file: file.relative.clone(),
            symbol,
        });
    }
    helper_types
}

fn private_entry_import_violations(
    references: &[Reference],
    entries: &[Entry],
) -> Vec<models::Violation> {
    let private = entries
        .iter()
        .filter(|entry| !entry.public_to_crate)
        .collect::<Vec<_>>();
    let mut violations: Vec<models::Violation> = Vec::new();
    for reference in references {
        for entry in &private {
            if !starts_with(&reference.target, &entry.module) {
                continue;
            }
            let same_package = entry
                .module
                .first()
                .is_some_and(|package| package == &reference.source_package);
            let same_domain = same_package && reference.source_domain == entry.domain;
            if !same_domain {
                violations.push(models::Violation::new(models::ViolationRequest {
                    code: "RSL104",
                    path: path::Path::new(&reference.source_file),
                    line: Some(reference.line),
                    message: format!(
                        "import reaches domain-private main entry {}",
                        entry.module.join("::")
                    ),
                    remediation:
                        "publish the main module to the crate or route through a public entry",
                }));
            }
            break;
        }
    }
    violations
}

fn unused_public_entry_violations(
    references: &[Reference],
    entries: &[Entry],
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for entry in entries {
        if !entry.public_to_crate || entry.externally_declared {
            continue;
        }
        let used_externally = references.iter().any(|reference| {
            reference.source_file != entry.file
                && starts_with(&reference.target, &entry.module)
                && (entry.module.first() != Some(&reference.source_package)
                    || reference.source_domain != entry.domain)
        });
        if !used_externally {
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RSL105",
                path: path::Path::new(&entry.file),
                line: None,
                message: "crate-visible main entry has no importer outside its owning domain",
                remediation: "restrict the module to its domain until an external importer exists",
            }));
        }
    }
    violations
}

fn private_helper_type_violations(
    references: &[Reference],
    helper_types: &[HelperType],
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for reference in references {
        for declaration in helper_types {
            if reference.target != declaration.symbol {
                continue;
            }
            if reference.source_file != declaration.file {
                violations.push(models::Violation::new(models::ViolationRequest {
                    code: "RSL110",
                    path: path::Path::new(&reference.source_file),
                    line: Some(reference.line),
                    message: format!(
                        "references file-private helper type {}",
                        declaration.symbol.join("::")
                    ),
                    remediation: "move a shared type to the owning models.rs or types.rs role",
                }));
            }
            break;
        }
    }
    violations
}

fn public_to_crate(visibility: &syn::Visibility) -> bool {
    match visibility {
        syn::Visibility::Public(_) => true,
        syn::Visibility::Restricted(restricted) => restricted.path.is_ident(CRATE_ROOT),
        syn::Visibility::Inherited => false,
    }
}

fn targets_bare_crate_surface(
    target: &[String],
    package: &str,
    module_visibility: &BTreeMap<Vec<String>, bool>,
) -> bool {
    target.len() == constants::MIN_DOMAIN_SEGMENTS
        && target.first().is_some_and(|root| root == package)
        && !module_visibility.contains_key(target)
}

fn is_crate_root(file: &models::SourceFile) -> bool {
    matches!(file.file_name(), constants::LIB_FILE | constants::MAIN_FILE)
}

fn is_test_source(file: &models::SourceFile) -> bool {
    file.file_name() == constants::INLINE_TEST_HARNESS_FILE
        || file.relative.contains("/tests/")
        || file
            .source
            .lines()
            .any(|line| line.trim() == TEST_ONLY_CRATE_ATTRIBUTE)
}

fn starts_with(target: &[String], prefix: &[String]) -> bool {
    target.len() >= prefix.len() && target[..prefix.len()] == *prefix
}
