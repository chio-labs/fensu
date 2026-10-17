use std::collections::HashMap;
use std::fs;
use std::path::Path;

use fensu_facts::parsing::main::parse_strict::parse_strict;
use ruff_python_ast::visitor::{walk_stmt, Visitor};
use ruff_python_ast::Stmt;
use syn::ext::IdentExt;
use syn::spanned::Spanned;

use crate::analyzer::AnalyzerId;
use crate::check::main::python_version::python_version;
use crate::models::{Config, RustExceptionSymbol};

const RUST_PATH_SEPARATOR: &str = "::";
const UNNAMED_RUST_ITEM: &str = "_";

pub(crate) fn validate_targets(config: &Config, project_root: &Path) -> Result<(), String> {
    for exception in &config.exceptions {
        let directory =
            if exception.rule == fensu_native::rules::constants::STALE_DEAD_CODE_ROOT_CODE {
                crate::configuration::main::configuration_directory::configuration_directory(
                    project_root,
                    &config.target_root,
                )
            } else {
                project_root.to_path_buf()
            };
        let path = directory.join(&exception.path);
        if !path.is_file() {
            return Err(format!(
                "Rule exception path does not exist: {}.",
                exception.path
            ));
        }
        if exception.symbols.is_empty() {
            continue;
        }
        let symbols = match config.analyzer {
            AnalyzerId::Python => defined_symbols(&path)?,
            AnalyzerId::Rust => defined_rust_symbols(&path)?,
            analyzer => defined_web_symbols(&path, analyzer)?,
        };
        for symbol in &exception.symbols {
            match symbols.get(symbol).copied().unwrap_or_default() {
                0 => {
                    return Err(format!(
                        "Rule exception symbol does not exist in {}: {symbol}.",
                        exception.path
                    ))
                }
                1 => {}
                _ => {
                    return Err(format!(
                        "Rule exception symbol is ambiguous in {}: {symbol}.",
                        exception.path
                    ))
                }
            }
        }
    }
    Ok(())
}

fn defined_rust_symbols(path: &Path) -> Result<HashMap<String, usize>, String> {
    let bytes = fs::read(path).map_err(|error| {
        format!(
            "Could not inspect rule exception path {}: {error}",
            path.display()
        )
    })?;
    let source = String::from_utf8_lossy(&bytes);
    let mut symbols: HashMap<String, usize> = HashMap::new();
    for symbol in rust_symbols(&source).map_err(|message| {
        format!(
            "Could not inspect rule exception path {}: {message}",
            path.display()
        )
    })? {
        *symbols.entry(symbol.name).or_default() += 1;
    }
    Ok(symbols)
}

fn defined_web_symbols(
    path: &Path,
    analyzer: AnalyzerId,
) -> Result<HashMap<String, usize>, String> {
    let bytes = fs::read(path).map_err(|error| {
        format!(
            "Could not inspect rule exception path {}: {error}",
            path.display()
        )
    })?;
    let facts: Vec<fensu_typescript::ModuleFacts> =
        if path.extension().and_then(|value| value.to_str()) == Some("svelte") {
            if analyzer != AnalyzerId::Svelte {
                return Err(format!(
                    "Could not inspect rule exception path {} with analyzer {analyzer}.",
                    path.display()
                ));
            }
            let parsed = fensu_svelte::parse(&bytes).map_err(|failure| {
                format!(
                    "Could not inspect rule exception path {}: {}",
                    path.display(),
                    failure.message
                )
            })?;
            let mut facts: Vec<fensu_typescript::ModuleFacts> = Vec::new();
            for script in parsed.scripts {
                facts.push(script.facts);
            }
            facts
        } else {
            let source_kind =
                crate::check::_helpers::project::source_kind(path).ok_or_else(|| {
                    format!(
                        "Could not inspect unsupported rule exception path {}.",
                        path.display()
                    )
                })?;
            vec![
                fensu_typescript::parse(&bytes, source_kind).map_err(|failure| {
                    format!(
                        "Could not inspect rule exception path {}: {}",
                        path.display(),
                        failure.message
                    )
                })?,
            ]
        };
    let mut symbols: HashMap<String, usize> = HashMap::new();
    for facts in facts {
        for function in &facts.functions {
            *symbols.entry(function.qualified_name.clone()).or_default() += 1;
            if function.qualified_name != function.name {
                *symbols.entry(function.name.clone()).or_default() += 1;
            }
        }
        for name in facts
            .classes
            .iter()
            .map(|item| item.name.as_str())
            .chain(facts.models.iter().map(|item| item.name.as_str()))
        {
            *symbols.entry(name.to_owned()).or_default() += 1;
        }
    }
    Ok(symbols)
}

fn defined_symbols(path: &Path) -> Result<HashMap<String, usize>, String> {
    let bytes = fs::read(path).map_err(|error| {
        format!(
            "Could not inspect rule exception path {}: {error}",
            path.display()
        )
    })?;
    let source = String::from_utf8_lossy(&bytes);
    let parsed = parse_strict(&source, python_version()).map_err(|failure| {
        format!(
            "Could not inspect rule exception path {}: {}",
            path.display(),
            failure.message
        )
    })?;
    let mut collector = SymbolCollector::default();
    collector.visit_body(&parsed.syntax().body);
    Ok(collector.symbols)
}

#[derive(Debug, Default)]
struct SymbolCollector {
    owners: Vec<String>,
    symbols: HashMap<String, usize>,
}

impl SymbolCollector {
    fn qualified(&self, name: &str) -> String {
        match self.owners.last() {
            Some(owner) => format!("{owner}.{name}"),
            None => name.to_owned(),
        }
    }
}

impl<'ast> Visitor<'ast> for SymbolCollector {
    fn visit_stmt(&mut self, statement: &'ast Stmt) {
        match statement {
            Stmt::FunctionDef(function) => {
                let symbol = self.qualified(function.name.as_str());
                *self.symbols.entry(symbol.clone()).or_default() += 1;
                self.owners.push(symbol);
                walk_stmt(self, statement);
                let _ = self.owners.pop();
            }
            Stmt::ClassDef(class) => {
                let symbol = self.qualified(class.name.as_str());
                self.owners.push(symbol);
                walk_stmt(self, statement);
                let _ = self.owners.pop();
            }
            _ => walk_stmt(self, statement),
        }
    }
}

pub(crate) fn rust_symbols(source: &str) -> Result<Vec<RustExceptionSymbol>, String> {
    let syntax = syn::parse_file(source).map_err(|error| error.to_string())?;
    Ok(item_symbols(&syntax.items, ""))
}

fn item_symbols(items: &[syn::Item], prefix: &str) -> Vec<RustExceptionSymbol> {
    let mut symbols: Vec<RustExceptionSymbol> = Vec::new();
    for item in items {
        match item {
            syn::Item::Fn(inner) => symbols.extend(symbol(prefix, &inner.sig.ident, item)),
            syn::Item::Struct(inner) => symbols.extend(symbol(prefix, &inner.ident, item)),
            syn::Item::Enum(inner) => symbols.extend(symbol(prefix, &inner.ident, item)),
            syn::Item::Union(inner) => symbols.extend(symbol(prefix, &inner.ident, item)),
            syn::Item::Type(inner) => symbols.extend(symbol(prefix, &inner.ident, item)),
            syn::Item::Const(inner) => symbols.extend(symbol(prefix, &inner.ident, item)),
            syn::Item::Static(inner) => symbols.extend(symbol(prefix, &inner.ident, item)),
            syn::Item::Trait(inner) => {
                symbols.extend(symbol(prefix, &inner.ident, item));
                symbols.extend(trait_symbols(inner, &qualified(prefix, &inner.ident)));
            }
            syn::Item::Impl(inner) => {
                if let Some(self_type) = self_type_path(&inner.self_ty) {
                    symbols.extend(impl_symbols(inner, &join(prefix, &self_type)));
                }
            }
            syn::Item::Mod(inner) => {
                if let Some((_, content)) = &inner.content {
                    symbols.extend(item_symbols(content, &qualified(prefix, &inner.ident)));
                }
            }
            _ => {}
        }
    }
    symbols
}

fn trait_symbols(item: &syn::ItemTrait, owner: &str) -> Vec<RustExceptionSymbol> {
    let mut symbols: Vec<RustExceptionSymbol> = Vec::new();
    for member in &item.items {
        let ident = match member {
            syn::TraitItem::Fn(inner) => &inner.sig.ident,
            syn::TraitItem::Const(inner) => &inner.ident,
            syn::TraitItem::Type(inner) => &inner.ident,
            _ => continue,
        };
        symbols.extend(symbol(owner, ident, member));
    }
    symbols
}

fn impl_symbols(item: &syn::ItemImpl, owner: &str) -> Vec<RustExceptionSymbol> {
    let mut symbols: Vec<RustExceptionSymbol> = Vec::new();
    for member in &item.items {
        let ident = match member {
            syn::ImplItem::Fn(inner) => &inner.sig.ident,
            syn::ImplItem::Const(inner) => &inner.ident,
            syn::ImplItem::Type(inner) => &inner.ident,
            _ => continue,
        };
        symbols.extend(symbol(owner, ident, member));
    }
    symbols
}

fn self_type_path(self_type: &syn::Type) -> Option<String> {
    let syn::Type::Path(path) = self_type else {
        return None;
    };
    if path.qself.is_some() {
        return None;
    }
    let segments: Vec<String> = path
        .path
        .segments
        .iter()
        .map(|segment| segment.ident.unraw().to_string())
        .collect();
    Some(segments.join(RUST_PATH_SEPARATOR))
}

fn symbol(prefix: &str, ident: &syn::Ident, node: &impl Spanned) -> Option<RustExceptionSymbol> {
    if ident == UNNAMED_RUST_ITEM {
        return None;
    }
    let span = node.span();
    Some(RustExceptionSymbol {
        name: qualified(prefix, ident),
        first_line: span.start().line,
        last_line: span.end().line,
    })
}

fn qualified(prefix: &str, ident: &syn::Ident) -> String {
    join(prefix, &ident.unraw().to_string())
}

fn join(prefix: &str, name: &str) -> String {
    if prefix.is_empty() {
        name.to_owned()
    } else {
        format!("{prefix}{RUST_PATH_SEPARATOR}{name}")
    }
}
