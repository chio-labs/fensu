use std::collections::HashMap;
use std::fs;
use std::path::Path;

use fensu_facts::parsing::main::parse_strict::parse_strict;
use ruff_python_ast::visitor::{walk_stmt, Visitor};
use ruff_python_ast::Stmt;

use crate::analyzer::AnalyzerId;
use crate::check::main::python_version::python_version;
use crate::models::Config;

pub(crate) fn validate_targets(config: &Config, project_root: &Path) -> Result<(), String> {
    for exception in &config.exceptions {
        let path = project_root.join(&exception.path);
        if !path.is_file() {
            return Err(format!(
                "Rule exception path does not exist: {}.",
                exception.path
            ));
        }
        if exception.symbols.is_empty() {
            continue;
        }
        let symbols = if config.analyzer == AnalyzerId::Python {
            defined_symbols(&path)?
        } else {
            defined_web_symbols(&path, config.analyzer)?
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
