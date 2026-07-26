//! Resolve the innermost qualified function symbol owning one source position.

use ruff_python_ast::visitor::{walk_stmt, Visitor};
use ruff_python_ast::{ModModule, Stmt};
use ruff_text_size::Ranged;

use crate::positions::models::LineIndex;

/// Return the innermost qualified function symbol containing the position.
pub(in crate::extension) fn owner_symbol_at(
    module: &ModModule,
    index: &LineIndex,
    line: u32,
    column: u32,
) -> Option<String> {
    let mut resolver = SymbolOwnerResolver {
        line,
        column,
        index,
        owners: Vec::new(),
        best_symbol: None,
        best_depth: 0,
    };
    resolver.visit_body(&module.body);
    resolver.best_symbol
}

#[derive(Debug)]
struct SymbolOwnerResolver<'a> {
    line: u32,
    column: u32,
    index: &'a LineIndex,
    owners: Vec<String>,
    best_symbol: Option<String>,
    best_depth: usize,
}

impl SymbolOwnerResolver<'_> {
    fn qualified(&self, name: &str) -> String {
        match self.owners.last() {
            Some(owner) => format!("{owner}.{name}"),
            None => name.to_owned(),
        }
    }

    fn contains(&self, statement: &Stmt) -> bool {
        let start = self.index.locate(statement.range().start().to_usize());
        let end = self.index.locate(statement.range().end().to_usize());
        (start.line, start.column) <= (self.line, self.column)
            && (self.line, self.column) < (end.line, end.column)
    }

    fn record_owner(&mut self, symbol: String) {
        let depth = symbol.split('.').count();
        if depth >= self.best_depth {
            self.best_depth = depth;
            self.best_symbol = Some(symbol.clone());
        }
        self.owners.push(symbol);
    }
}

impl<'ast> Visitor<'ast> for SymbolOwnerResolver<'_> {
    fn visit_stmt(&mut self, statement: &'ast Stmt) {
        match statement {
            Stmt::FunctionDef(function) => {
                if !self.contains(statement) {
                    return;
                }
                let symbol = self.qualified(function.name.as_str());
                self.record_owner(symbol);
                walk_stmt(self, statement);
                let _ = self.owners.pop();
            }
            Stmt::ClassDef(class) => {
                if !self.contains(statement) {
                    return;
                }
                let symbol = self.qualified(class.name.as_str());
                self.owners.push(symbol);
                walk_stmt(self, statement);
                let _ = self.owners.pop();
            }
            _ => walk_stmt(self, statement),
        }
    }
}
