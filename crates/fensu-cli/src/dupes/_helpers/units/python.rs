//! Extract normalised function and method units from Python sources.

use std::collections::HashSet;

use fensu_facts::parsing::main::parse_strict::parse_strict;
use ruff_python_ast::token::{Token, TokenKind};
use ruff_python_ast::visitor::{walk_expr, walk_stmt, Visitor};
use ruff_python_ast::{
    ElifElseClause, Expr, Parameters, PythonVersion, Stmt, StmtClassDef, StmtFunctionDef,
};
use ruff_text_size::{Ranged, TextSize};

use crate::dupes::_helpers::units::lines::LineIndex;
use crate::dupes::constants::{
    MARKER_DEDENT, MARKER_INDENT, MARKER_NEWLINE, PLACEHOLDER_FSTRING, PLACEHOLDER_IDENTIFIER,
    PLACEHOLDER_NUMBER, PLACEHOLDER_STRING,
};
use crate::dupes::models::ExtractedUnit;

struct IgnoredSpan {
    start: TextSize,
    end: TextSize,
    statement: bool,
}

#[derive(Default)]
struct SyntaxMarks {
    call_targets: HashSet<TextSize>,
    ignored: Vec<IgnoredSpan>,
}

/// Return one unit per top-level function or class method, excluding decorators.
pub(crate) fn extract_python_units(source: &str) -> Vec<ExtractedUnit> {
    let Ok(parsed) = parse_strict(source, PythonVersion::latest()) else {
        return Vec::new();
    };
    let tokens: Vec<&Token> = parsed
        .tokens()
        .iter()
        .filter(|token| {
            !matches!(
                token.kind(),
                TokenKind::Comment | TokenKind::NonLogicalNewline | TokenKind::EndOfFile
            )
        })
        .collect();
    let mut marks = SyntaxMarks::default();
    for statement in &parsed.syntax().body {
        marks.visit_stmt(statement);
    }
    let starts: Vec<TextSize> = tokens.iter().map(|token| token.start()).collect();
    let mut normalized: Vec<Option<String>> = tokens
        .iter()
        .map(|token| normalize(source, token, &marks.call_targets))
        .collect();
    for span in &marks.ignored {
        let mut end = starts.partition_point(|start| *start < span.end);
        if span.statement
            && tokens
                .get(end)
                .is_some_and(|token| token.kind() == TokenKind::Newline)
        {
            end += 1;
        }
        let first = starts.partition_point(|start| *start < span.start);
        for slot in normalized.iter_mut().take(end).skip(first) {
            *slot = None;
        }
    }
    let lines = LineIndex::new(source);
    collect_functions(&parsed.syntax().body, "")
        .into_iter()
        .map(|(name, function)| {
            let start = definition_start(function, &tokens);
            let first = starts.partition_point(|offset| *offset < start);
            let last = starts.partition_point(|offset| *offset < function.end());
            let mut unit = ExtractedUnit {
                name,
                start_line: lines.line(start.to_usize()),
                end_line: lines.end_line(start.to_usize(), function.end().to_usize()),
                ..ExtractedUnit::default()
            };
            for index in first..last {
                if let Some(text) = &normalized[index] {
                    unit.normalized.push(text.clone());
                    unit.concrete
                        .push(concrete_text(source, tokens[index], text));
                }
            }
            unit
        })
        .collect()
}

fn normalize(source: &str, token: &Token, call_targets: &HashSet<TextSize>) -> Option<String> {
    let kind = token.kind();
    let text = &source[token.range()];
    let placeholder = match kind {
        TokenKind::Name => {
            return Some(name_text(text, token, call_targets));
        }
        _ if kind.is_soft_keyword() => return Some(name_text(text, token, call_targets)),
        TokenKind::Rarrow
        | TokenKind::FStringMiddle
        | TokenKind::FStringEnd
        | TokenKind::TStringMiddle
        | TokenKind::TStringEnd => return None,
        TokenKind::Int | TokenKind::Float | TokenKind::Complex => PLACEHOLDER_NUMBER,
        TokenKind::String => PLACEHOLDER_STRING,
        TokenKind::FStringStart | TokenKind::TStringStart => PLACEHOLDER_FSTRING,
        TokenKind::Newline => MARKER_NEWLINE,
        TokenKind::Indent => MARKER_INDENT,
        TokenKind::Dedent => MARKER_DEDENT,
        _ => text,
    };
    Some(placeholder.to_owned())
}

/// Spell layout tokens by their marker so re-indented copies still compare as exact.
fn concrete_text(source: &str, token: &Token, normalized: &str) -> String {
    match token.kind() {
        TokenKind::Newline | TokenKind::Indent | TokenKind::Dedent => normalized.to_owned(),
        _ => source[token.range()].to_owned(),
    }
}

fn name_text(text: &str, token: &Token, call_targets: &HashSet<TextSize>) -> String {
    if call_targets.contains(&token.start()) {
        text.to_owned()
    } else {
        PLACEHOLDER_IDENTIFIER.to_owned()
    }
}

fn definition_start(function: &StmtFunctionDef, tokens: &[&Token]) -> TextSize {
    let Some(decorator) = function.decorator_list.last() else {
        return function.start();
    };
    tokens
        .iter()
        .find(|token| {
            token.start() >= decorator.end()
                && matches!(token.kind(), TokenKind::Def | TokenKind::Async)
        })
        .map_or(function.start(), |token| token.start())
}

fn collect_functions<'a>(body: &'a [Stmt], prefix: &str) -> Vec<(String, &'a StmtFunctionDef)> {
    let mut collected: Vec<(String, &'a StmtFunctionDef)> = Vec::new();
    for statement in body {
        match statement {
            Stmt::FunctionDef(function) => {
                collected.push((format!("{prefix}{}", function.name.id), function));
            }
            Stmt::ClassDef(class) => {
                collected.extend(collect_functions(
                    &class.body,
                    &format!("{prefix}{}.", class.name.id),
                ));
            }
            Stmt::If(branch) => {
                collected.extend(collect_functions(&branch.body, prefix));
                for clause in &branch.elif_else_clauses {
                    collected.extend(collect_clause(clause, prefix));
                }
            }
            Stmt::Try(attempt) => {
                collected.extend(collect_functions(&attempt.body, prefix));
                collected.extend(collect_functions(&attempt.orelse, prefix));
            }
            _ => {}
        }
    }
    collected
}

fn collect_clause<'a>(
    clause: &'a ElifElseClause,
    prefix: &str,
) -> Vec<(String, &'a StmtFunctionDef)> {
    collect_functions(&clause.body, prefix)
}

impl SyntaxMarks {
    fn docstring(&mut self, body: &[Stmt]) {
        if let Some(Stmt::Expr(expression)) = body.first() {
            if expression.value.is_string_literal_expr() {
                self.ignored.push(IgnoredSpan {
                    start: expression.start(),
                    end: expression.end(),
                    statement: true,
                });
            }
        }
    }

    fn annotation(&mut self, owner_end: TextSize, annotation: &Expr) {
        self.ignored.push(IgnoredSpan {
            start: owner_end,
            end: annotation.end(),
            statement: false,
        });
    }

    fn signature(&mut self, function: &StmtFunctionDef) {
        if let Some(returns) = &function.returns {
            self.ignored.push(IgnoredSpan {
                start: returns.start(),
                end: returns.end(),
                statement: false,
            });
        }
        self.parameters(&function.parameters);
    }

    fn parameters(&mut self, parameters: &Parameters) {
        for parameter in parameters.iter() {
            let parameter = parameter.as_parameter();
            if let Some(annotation) = &parameter.annotation {
                self.annotation(parameter.name.end(), annotation);
            }
        }
    }

    fn class(&mut self, class: &StmtClassDef) {
        self.docstring(&class.body);
    }
}

impl<'a> Visitor<'a> for SyntaxMarks {
    fn visit_stmt(&mut self, stmt: &'a Stmt) {
        match stmt {
            Stmt::FunctionDef(function) => {
                self.docstring(&function.body);
                self.signature(function);
            }
            Stmt::ClassDef(class) => self.class(class),
            Stmt::AnnAssign(assignment) => {
                self.annotation(assignment.target.end(), &assignment.annotation);
            }
            _ => {}
        }
        walk_stmt(self, stmt);
    }

    fn visit_expr(&mut self, expr: &'a Expr) {
        if let Expr::Call(call) = expr {
            match call.func.as_ref() {
                Expr::Name(name) => {
                    self.call_targets.insert(name.start());
                }
                Expr::Attribute(attribute) => {
                    self.call_targets.insert(attribute.attr.start());
                }
                _ => {}
            }
        }
        walk_expr(self, expr);
    }
}
