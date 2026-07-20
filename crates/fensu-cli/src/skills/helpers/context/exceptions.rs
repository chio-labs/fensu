use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;

use fensu_facts::parsing::main::parse_strict::parse_strict;
use ruff_python_ast::visitor::{walk_stmt, Visitor};
use ruff_python_ast::Stmt;

use crate::helpers::check_policy::python_version;
use crate::models::{Config, RuleMetadata};

pub(crate) fn validate(
    config: &Config,
    catalogue: &[RuleMetadata],
    project_root: &Path,
) -> Result<(), String> {
    let codes = catalogue
        .iter()
        .map(|item| item.code.as_str())
        .collect::<HashSet<_>>();
    for exception in &config.exceptions {
        if !codes.contains(exception.rule.as_str()) {
            return Err(format!("Unknown rule exception code: {}.", exception.rule));
        }
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
        let symbols = defined_symbols(&path)?;
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

#[derive(Default)]
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

impl<'a> Visitor<'a> for SymbolCollector {
    fn visit_stmt(&mut self, statement: &'a Stmt) {
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
