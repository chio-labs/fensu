//! Collect versioned parser-independent facts from one discovered Cargo workspace.

use std::collections::BTreeMap;
use std::path::Path;

use quote::ToTokens;
use syn::parse::Parser;
use syn::spanned::Spanned;

use crate::constants::{BINARY_TARGET_KIND, CRATE_PATH_ROOT, SELF_PATH_ROOT, SUPER_PATH_ROOT};
use crate::constants::{FACT_SCHEMA_VERSION, PARSER_CONTRACT_VERSION};
use crate::facts::models::{
    RustCrateFact, RustDependencyFact, RustFileFact, RustItemFact, RustSourcePosition,
    RustSourceRange, RustTargetFact, RustUseFact, RustWorkspaceFacts,
};
use crate::models::{SourceFile, WorkspaceCrate};
use crate::rules::main::relative_display::relative_display;
use crate::rules::main::use_paths::use_paths;

#[derive(Clone)]
struct FileSeed {
    file: SourceFile,
    crate_identity: String,
    crate_name: String,
    module_parts: Vec<String>,
    crate_root_parts: Vec<String>,
    source_root: String,
    test: bool,
}

/// Build one deterministic fact payload without exposing Cargo or syn types.
pub(crate) fn collect(
    repository_root: &Path,
    workspace_crates: &[WorkspaceCrate],
) -> RustWorkspaceFacts {
    let seeds = file_seeds(workspace_crates);
    let module_index = seeds
        .values()
        .map(|seed| {
            (
                seed.module_parts.clone(),
                (seed.file.relative.clone(), seed.crate_identity.clone()),
            )
        })
        .collect::<BTreeMap<_, _>>();
    let crates: Vec<RustCrateFact> = workspace_crates
        .iter()
        .map(|workspace_crate| crate_fact(repository_root, workspace_crate, workspace_crates))
        .collect();
    let files: Vec<RustFileFact> = seeds
        .into_values()
        .map(|seed| file_fact(seed, workspace_crates, &module_index))
        .collect();
    RustWorkspaceFacts {
        schema_version: FACT_SCHEMA_VERSION.to_owned(),
        parser_contract: PARSER_CONTRACT_VERSION.to_owned(),
        crates,
        files,
    }
}

fn file_seeds(workspace_crates: &[WorkspaceCrate]) -> BTreeMap<String, FileSeed> {
    let mut seeds: BTreeMap<String, FileSeed> = BTreeMap::new();
    for workspace_crate in workspace_crates {
        let crate_name = workspace_crate
            .package_name
            .clone()
            .unwrap_or_else(|| workspace_crate.package_identity.clone());
        let module_root = workspace_crate
            .source_name()
            .unwrap_or_else(|| crate_name.replace('-', "_"));
        for file in &workspace_crate.files {
            let module_parts = module_parts(&module_root, file);
            let crate_root_parts = if is_binary_entry(file, &workspace_crate.targets) {
                module_parts.clone()
            } else {
                vec![module_root.clone()]
            };
            let source_root = file.source_root_relative.clone();
            let test = workspace_crate
                .targets
                .iter()
                .filter(|target| file.path.starts_with(&target.source_root))
                .max_by_key(|target| target.source_root.components().count())
                .is_some_and(|target| target.test);
            seeds.entry(file.relative.clone()).or_insert(FileSeed {
                file: file.clone(),
                crate_identity: workspace_crate.package_identity.clone(),
                crate_name: crate_name.clone(),
                module_parts,
                crate_root_parts,
                source_root,
                test,
            });
        }
    }
    seeds
}

fn is_binary_entry(file: &SourceFile, targets: &[crate::models::WorkspaceTarget]) -> bool {
    for target in targets {
        if target.entry_path == file.path && target_has_kind(target, BINARY_TARGET_KIND) {
            return true;
        }
    }
    false
}

fn target_has_kind(target: &crate::models::WorkspaceTarget, expected: &str) -> bool {
    target.kinds.iter().any(|kind| kind == expected)
}

fn module_parts(root: &str, file: &SourceFile) -> Vec<String> {
    let mut parts = file
        .source_relative
        .split('/')
        .map(str::to_owned)
        .collect::<Vec<_>>();
    let Some(name) = parts.pop() else {
        return vec![root.to_owned()];
    };
    if name == crate::constants::MAIN_FILE {
        parts.push("main".to_owned());
    } else if !matches!(name.as_str(), "lib.rs" | "mod.rs") {
        parts.push(name.trim_end_matches(".rs").to_owned());
    }
    let mut module = vec![root.to_owned()];
    module.extend(parts);
    module
}

fn crate_fact(
    repository_root: &Path,
    workspace_crate: &WorkspaceCrate,
    workspace_crates: &[WorkspaceCrate],
) -> RustCrateFact {
    let mut targets = workspace_crate
        .targets
        .iter()
        .map(|target| {
            let mut kinds = target.kinds.clone();
            kinds.sort();
            kinds.dedup();
            RustTargetFact {
                identity: format!(
                    "{}:{}:{}",
                    workspace_crate.package_identity,
                    target.name,
                    relative_display(repository_root, &target.entry_path)
                ),
                name: target.name.clone(),
                kinds,
                source_root: relative_display(repository_root, &target.source_root),
                entry_path: relative_display(repository_root, &target.entry_path),
                test: target.test,
            }
        })
        .collect::<Vec<_>>();
    targets.sort();
    targets.dedup();
    let mut dependency_by_identity: BTreeMap<(String, String, Vec<String>), RustDependencyFact> =
        BTreeMap::new();
    for dependency in &workspace_crate.dependencies {
        let mut kinds = dependency.kinds.clone();
        kinds.sort();
        kinds.dedup();
        let identity = (
            dependency.package_name.clone(),
            dependency.source_name.clone(),
            kinds.clone(),
        );
        let local = local_crate_identity(dependency.path.as_deref(), workspace_crates);
        let value = dependency_by_identity
            .entry(identity)
            .or_insert(RustDependencyFact {
                package_name: dependency.package_name.clone(),
                source_name: dependency.source_name.clone(),
                kinds,
                local_crate_identity: local.clone(),
                resolved: dependency.resolved,
            });
        value.resolved |= dependency.resolved;
        if value.local_crate_identity.is_none() {
            value.local_crate_identity = local;
        }
    }
    let mut dependencies = dependency_by_identity.into_values().collect::<Vec<_>>();
    dependencies.sort();
    dependencies.dedup();
    RustCrateFact {
        identity: workspace_crate.package_identity.clone(),
        name: workspace_crate
            .package_name
            .clone()
            .unwrap_or_else(|| workspace_crate.package_identity.clone()),
        directory: relative_display(repository_root, &workspace_crate.directory),
        manifest_path: relative_display(
            repository_root,
            &workspace_crate
                .directory
                .join(crate::constants::CARGO_MANIFEST_FILE),
        ),
        library_name: workspace_crate.library_name.clone(),
        targets,
        dependencies,
    }
}

fn local_crate_identity(
    path: Option<&Path>,
    workspace_crates: &[WorkspaceCrate],
) -> Option<String> {
    let path = path?;
    for workspace_crate in workspace_crates {
        if workspace_crate.directory == path {
            return Some(workspace_crate.package_identity.clone());
        }
    }
    None
}

fn file_fact(
    seed: FileSeed,
    workspace_crates: &[WorkspaceCrate],
    module_index: &BTreeMap<Vec<String>, (String, String)>,
) -> RustFileFact {
    let (items, uses, parse_error) = match (&seed.file.syntax.file, &seed.file.syntax.error) {
        (Some(syntax), _) => {
            let items = collect_items(&seed.file.relative, &syntax.items, &seed.module_parts);
            let uses = collect_uses(&seed, &syntax.items, workspace_crates, module_index);
            (items, uses, None)
        }
        (None, Some(error)) => (Vec::new(), Vec::new(), Some(error.message.clone())),
        (None, None) => (
            Vec::new(),
            Vec::new(),
            Some("Rust parser returned no result".to_owned()),
        ),
    };
    RustFileFact {
        path: seed.file.relative,
        crate_identity: seed.crate_identity,
        crate_name: seed.crate_name,
        module_parts: seed.module_parts,
        source_root: seed.source_root,
        test: seed.test,
        source: seed.file.source,
        parse_error,
        items,
        uses,
    }
}

fn collect_items(path: &str, items: &[syn::Item], module_parts: &[String]) -> Vec<RustItemFact> {
    let mut facts: Vec<RustItemFact> = Vec::new();
    for item in items {
        if let Some(fact) = item_fact(path, item, module_parts) {
            facts.push(fact);
        }
        if let syn::Item::Mod(module) = item {
            if let Some((_, nested)) = &module.content {
                let mut child_module = module_parts.to_vec();
                child_module.push(module.ident.to_string());
                facts.extend(collect_items(path, nested, &child_module));
            }
        }
    }
    facts.sort();
    facts
}

fn item_fact(path: &str, item: &syn::Item, module_parts: &[String]) -> Option<RustItemFact> {
    let (kind, name, visibility, attributes, implemented_trait, implementation_target, span) =
        match item {
            syn::Item::Fn(value) => (
                "function",
                Some(value.sig.ident.to_string()),
                visibility_name(&value.vis),
                value.attrs.as_slice(),
                None,
                None,
                value.sig.ident.span(),
            ),
            syn::Item::Struct(value) => (
                "struct",
                Some(value.ident.to_string()),
                visibility_name(&value.vis),
                value.attrs.as_slice(),
                None,
                None,
                value.ident.span(),
            ),
            syn::Item::Enum(value) => (
                "enum",
                Some(value.ident.to_string()),
                visibility_name(&value.vis),
                value.attrs.as_slice(),
                None,
                None,
                value.ident.span(),
            ),
            syn::Item::Trait(value) => (
                "trait",
                Some(value.ident.to_string()),
                visibility_name(&value.vis),
                value.attrs.as_slice(),
                None,
                None,
                value.ident.span(),
            ),
            syn::Item::Impl(value) => (
                "implementation",
                None,
                "private".to_owned(),
                value.attrs.as_slice(),
                value
                    .trait_
                    .as_ref()
                    .map(|(_, path, _)| compact_tokens(path)),
                Some(compact_tokens(value.self_ty.as_ref())),
                value.impl_token.span,
            ),
            syn::Item::Mod(value) => (
                "module",
                Some(value.ident.to_string()),
                visibility_name(&value.vis),
                value.attrs.as_slice(),
                None,
                None,
                value.ident.span(),
            ),
            _ => return None,
        };
    Some(RustItemFact {
        kind: kind.to_owned(),
        name,
        module_parts: module_parts.to_vec(),
        visibility,
        derives: derives(attributes),
        implemented_trait,
        implementation_target,
        location: source_range(path, span),
    })
}

fn derives(attributes: &[syn::Attribute]) -> Vec<String> {
    let parser = syn::punctuated::Punctuated::<syn::Path, syn::Token![,]>::parse_terminated;
    let mut values: Vec<String> = Vec::new();
    for attribute in attributes
        .iter()
        .filter(|attribute| attribute.path().is_ident("derive"))
    {
        let Ok(list) = attribute.meta.require_list() else {
            continue;
        };
        let Ok(paths) = parser.parse2(list.tokens.clone()) else {
            continue;
        };
        values.extend(paths.into_iter().map(|path| compact_tokens(&path)));
    }
    values.sort();
    values.dedup();
    values
}

fn visibility_name(visibility: &syn::Visibility) -> String {
    match visibility {
        syn::Visibility::Public(_) => "public".to_owned(),
        syn::Visibility::Restricted(value) if value.path.is_ident("crate") => "crate".to_owned(),
        syn::Visibility::Restricted(value) => format!("restricted:{}", compact_tokens(&value.path)),
        syn::Visibility::Inherited => "private".to_owned(),
    }
}

fn compact_tokens(value: &impl ToTokens) -> String {
    value.to_token_stream().to_string().replace(' ', "")
}

fn collect_uses(
    seed: &FileSeed,
    items: &[syn::Item],
    workspace_crates: &[WorkspaceCrate],
    module_index: &BTreeMap<Vec<String>, (String, String)>,
) -> Vec<RustUseFact> {
    let mut facts: Vec<RustUseFact> = Vec::new();
    for item in items {
        match item {
            syn::Item::Use(value) => {
                for authored_parts in use_paths(&value.tree) {
                    facts.push(use_fact(UseFactRequest {
                        seed,
                        authored_parts,
                        span: value.span(),
                        workspace_crates,
                        module_index,
                    }));
                }
            }
            syn::Item::Mod(module) => {
                if let Some((_, nested)) = &module.content {
                    let mut child = seed.clone();
                    child.module_parts.push(module.ident.to_string());
                    facts.extend(collect_uses(&child, nested, workspace_crates, module_index));
                }
            }
            _ => {}
        }
    }
    facts.sort();
    facts
}

struct UseFactRequest<'a> {
    seed: &'a FileSeed,
    authored_parts: Vec<String>,
    span: proc_macro2::Span,
    workspace_crates: &'a [WorkspaceCrate],
    module_index: &'a BTreeMap<Vec<String>, (String, String)>,
}

fn use_fact(request: UseFactRequest<'_>) -> RustUseFact {
    let UseFactRequest {
        seed,
        authored_parts,
        span,
        workspace_crates,
        module_index,
    } = request;
    let source_crate = workspace_crates
        .iter()
        .find(|candidate| candidate.package_identity == seed.crate_identity);
    let (candidate, root_identity, known_external) = resolved_use_candidate(ResolveUseRequest {
        authored: &authored_parts,
        source_module: &seed.module_parts,
        source_crate_root: &seed.crate_root_parts,
        source_crate,
        workspace_crates,
    });
    let target = candidate.as_ref().and_then(|candidate| {
        module_index
            .iter()
            .filter(|(module, _)| candidate.starts_with(module.as_slice()))
            .max_by_key(|(module, _)| module.len())
            .filter(|(module, _)| candidate.len() <= module.len() + 1)
    });
    let (target_module_parts, target_path, target_crate_identity, resolution) = match target {
        Some((module, (path, identity))) => (
            Some(module.clone()),
            Some(path.clone()),
            Some(identity.clone()),
            "resolved",
        ),
        None if known_external => (None, None, None, "external"),
        None if root_identity.is_some() => (None, None, root_identity, "crate"),
        None => (None, None, None, "unresolved"),
    };
    RustUseFact {
        source_path: seed.file.relative.clone(),
        source_module_parts: seed.module_parts.clone(),
        authored_parts,
        target_module_parts,
        target_path,
        target_crate_identity,
        resolution: resolution.to_owned(),
        location: source_range(&seed.file.relative, span),
    }
}

struct ResolveUseRequest<'a> {
    authored: &'a [String],
    source_module: &'a [String],
    source_crate_root: &'a [String],
    source_crate: Option<&'a WorkspaceCrate>,
    workspace_crates: &'a [WorkspaceCrate],
}

fn resolved_use_candidate(
    request: ResolveUseRequest<'_>,
) -> (Option<Vec<String>>, Option<String>, bool) {
    let ResolveUseRequest {
        authored,
        source_module,
        source_crate_root,
        source_crate,
        workspace_crates,
    } = request;
    let Some(root) = authored.first() else {
        return (None, None, false);
    };
    if root == CRATE_PATH_ROOT {
        let mut value = source_crate_root.to_vec();
        value.extend_from_slice(&authored[1..]);
        return (
            Some(value),
            source_crate.map(|value| value.package_identity.clone()),
            false,
        );
    }
    if root == SELF_PATH_ROOT {
        let mut value = source_module.to_vec();
        value.extend_from_slice(&authored[1..]);
        return (
            Some(value),
            source_crate.map(|value| value.package_identity.clone()),
            false,
        );
    }
    if root == SUPER_PATH_ROOT {
        let count = authored
            .iter()
            .take_while(|part| part.as_str() == SUPER_PATH_ROOT)
            .count();
        let mut value = source_module
            .iter()
            .take(source_module.len().saturating_sub(count))
            .cloned()
            .collect::<Vec<_>>();
        value.extend_from_slice(&authored[count..]);
        return (
            Some(value),
            source_crate.map(|value| value.package_identity.clone()),
            false,
        );
    }
    let Some(source_crate) = source_crate else {
        return (None, None, false);
    };
    if source_crate.source_name().as_deref() == Some(root) {
        return (
            Some(authored.to_vec()),
            Some(source_crate.package_identity.clone()),
            false,
        );
    }
    let Some(dependency) = source_crate
        .dependencies
        .iter()
        .find(|dependency| dependency.source_name == *root)
    else {
        return (None, None, false);
    };
    let local = dependency.path.as_ref().and_then(|path| {
        workspace_crates
            .iter()
            .find(|candidate| candidate.directory == *path)
    });
    match local {
        Some(target_crate) => {
            let mut value = vec![target_crate.source_name().unwrap_or_else(|| root.clone())];
            value.extend_from_slice(&authored[1..]);
            (
                Some(value),
                Some(target_crate.package_identity.clone()),
                false,
            )
        }
        None => (None, None, true),
    }
}

fn source_range(path: &str, span: proc_macro2::Span) -> RustSourceRange {
    let start = span.start();
    let end = span.end();
    RustSourceRange {
        path: path.to_owned(),
        start: RustSourcePosition {
            line: start.line,
            column: start.column,
        },
        end: RustSourcePosition {
            line: end.line,
            column: end.column,
        },
    }
}
