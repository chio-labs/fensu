//! Extract normalised function units from TypeScript, JavaScript, and Svelte sources.

use std::collections::HashSet;
use std::path::Path;

use oxc_allocator::Allocator;
use oxc_ast::ast::{
    BindingIdentifier, CallExpression, Class, ClassElement, Declaration,
    ExportDefaultDeclarationKind, Expression, Function, IdentifierName, IdentifierReference,
    LabelIdentifier, NewExpression, PrivateIdentifier, Statement, TSTypeAnnotation,
    TSTypeParameterDeclaration, VariableDeclaration,
};
use oxc_ast_visit::{walk, Visit};
use oxc_parser::config::TokensParserConfig;
use oxc_parser::{Kind, Parser, ParserReturn, Token};
use oxc_span::{GetSpan, SourceType, Span};

use crate::dupes::_helpers::units::lines::LineIndex;
use crate::dupes::constants::{
    PLACEHOLDER_IDENTIFIER, PLACEHOLDER_NUMBER, PLACEHOLDER_REGEX, PLACEHOLDER_STRING,
    PLACEHOLDER_TEMPLATE,
};
use crate::dupes::models::ExtractedUnit;

#[derive(Default)]
struct SyntaxMarks {
    names: HashSet<u32>,
    call_targets: HashSet<u32>,
    ignored: Vec<Span>,
}

const DEFAULT_EXPORT: &str = "default";

struct UnitSpan {
    name: String,
    start: u32,
    end: u32,
}

/// Return units for one TypeScript or JavaScript module.
pub(crate) fn extract_script_units(path: &Path, source: &str) -> Vec<ExtractedUnit> {
    let source_type = SourceType::from_path(path).unwrap_or_else(|_| SourceType::ts());
    extract_with_type(source, source_type)
}

/// Return units for every `<script>` block of one Svelte component.
pub(crate) fn extract_svelte_units(source: &str) -> Vec<ExtractedUnit> {
    let Ok(facts) = fensu_svelte::parse(source.as_bytes()) else {
        return Vec::new();
    };
    let mut units: Vec<ExtractedUnit> = Vec::new();
    for script in facts.scripts {
        let Some(content) = source.get(script.content_span.start..script.content_span.end) else {
            continue;
        };
        let offset = script.content_span.line.saturating_sub(1);
        units.extend(
            extract_with_type(content, SourceType::ts())
                .into_iter()
                .map(|mut unit| {
                    unit.start_line += offset;
                    unit.end_line += offset;
                    unit
                }),
        );
    }
    units
}

fn extract_with_type(source: &str, source_type: SourceType) -> Vec<ExtractedUnit> {
    let allocator = Allocator::default();
    let parsed: ParserReturn<'_> = Parser::new(&allocator, source, source_type)
        .with_config(TokensParserConfig)
        .parse();
    if parsed.panicked || !parsed.diagnostics.is_empty() {
        return Vec::new();
    }
    let mut marks = SyntaxMarks::default();
    marks.visit_program(&parsed.program);
    let spans: Vec<UnitSpan> = parsed
        .program
        .body
        .iter()
        .flat_map(statement_units)
        .collect();
    let tokens: Vec<&Token> = parsed.tokens.iter().collect();
    let mut normalized: Vec<Option<String>> = tokens
        .iter()
        .map(|token| normalize(source, token, &marks))
        .collect();
    for span in &marks.ignored {
        let first = tokens.partition_point(|token| token.start() < span.start);
        let last = tokens.partition_point(|token| token.start() < span.end);
        for slot in normalized.iter_mut().take(last).skip(first) {
            *slot = None;
        }
    }
    let lines = LineIndex::new(source);
    spans
        .into_iter()
        .map(|span| {
            let first = tokens.partition_point(|token| token.start() < span.start);
            let last = tokens.partition_point(|token| token.start() < span.end);
            let start = tokens.get(first).map_or(span.start, |token| token.start());
            let mut unit = ExtractedUnit {
                name: span.name,
                start_line: lines.line(start as usize),
                end_line: lines.end_line(span.start as usize, span.end as usize),
                ..ExtractedUnit::default()
            };
            for index in first..last {
                if let Some(text) = &normalized[index] {
                    unit.normalized.push(text.clone());
                    unit.concrete
                        .push(token_text(source, tokens[index]).to_owned());
                }
            }
            unit
        })
        .collect()
}

fn token_text<'s>(source: &'s str, token: &Token) -> &'s str {
    source
        .get(token.start() as usize..token.end() as usize)
        .unwrap_or_default()
}

fn normalize(source: &str, token: &Token, marks: &SyntaxMarks) -> Option<String> {
    let text = token_text(source, token);
    if marks.names.contains(&token.start()) {
        return Some(if marks.call_targets.contains(&token.start()) {
            text.to_owned()
        } else {
            PLACEHOLDER_IDENTIFIER.to_owned()
        });
    }
    let kind = token.kind();
    let placeholder = match kind {
        Kind::TemplateMiddle | Kind::TemplateTail => return None,
        Kind::JSXText if text.trim().is_empty() => return None,
        Kind::Str | Kind::JSXText => PLACEHOLDER_STRING,
        Kind::NoSubstitutionTemplate | Kind::TemplateHead => PLACEHOLDER_TEMPLATE,
        Kind::RegExp => PLACEHOLDER_REGEX,
        Kind::Ident | Kind::PrivateIdentifier => PLACEHOLDER_IDENTIFIER,
        _ if kind.is_number() => PLACEHOLDER_NUMBER,
        _ => text,
    };
    Some(placeholder.to_owned())
}

fn statement_units(statement: &Statement<'_>) -> Vec<UnitSpan> {
    match statement {
        Statement::FunctionDeclaration(function) => function_unit(function, None),
        Statement::ClassDeclaration(class) => class_units(class),
        Statement::VariableDeclaration(declaration) => variable_units(declaration),
        Statement::ExportDeclaration(export) => match &export.declaration {
            Declaration::FunctionDeclaration(function) => function_unit(function, None),
            Declaration::ClassDeclaration(class) => class_units(class),
            Declaration::VariableDeclaration(declaration) => variable_units(declaration),
            _ => Vec::new(),
        },
        Statement::ExportDefaultDeclaration(export) => match &export.declaration {
            ExportDefaultDeclarationKind::FunctionDeclaration(function) => {
                function_unit(function, Some(DEFAULT_EXPORT.to_owned()))
            }
            ExportDefaultDeclarationKind::ClassDeclaration(class) => class_units(class),
            _ => Vec::new(),
        },
        _ => Vec::new(),
    }
}

fn function_unit(function: &Function<'_>, fallback: Option<String>) -> Vec<UnitSpan> {
    let name = function
        .id
        .as_ref()
        .map(|id| id.name.to_string())
        .or(fallback);
    match (name, &function.body) {
        (Some(name), Some(_)) => vec![UnitSpan {
            name,
            start: function.span.start,
            end: function.span.end,
        }],
        _ => Vec::new(),
    }
}

fn class_units(class: &Class<'_>) -> Vec<UnitSpan> {
    let class_name = class
        .id
        .as_ref()
        .map_or_else(|| DEFAULT_EXPORT.to_owned(), |id| id.name.to_string());
    class
        .body
        .body
        .iter()
        .filter_map(|element| member_unit(&class_name, element))
        .collect()
}

fn member_unit(class_name: &str, element: &ClassElement<'_>) -> Option<UnitSpan> {
    let member = element.static_name()?;
    let (span, decorated_end, callable) = match element {
        ClassElement::MethodDefinition(method) => (
            method.span,
            method.decorators.last().map(|decorator| decorator.span.end),
            method.value.body.is_some(),
        ),
        ClassElement::PropertyDefinition(property) => (
            property.span,
            property
                .decorators
                .last()
                .map(|decorator| decorator.span.end),
            property.value.as_ref().is_some_and(is_function_expression),
        ),
        _ => return None,
    };
    callable.then(|| UnitSpan {
        name: format!("{class_name}.{member}"),
        start: decorated_end.unwrap_or(span.start).max(span.start),
        end: span.end,
    })
}

fn variable_units(declaration: &VariableDeclaration<'_>) -> Vec<UnitSpan> {
    let mut spans: Vec<UnitSpan> = Vec::new();
    for (position, declarator) in declaration.declarations.iter().enumerate() {
        let Some(identifier) = declarator.id.get_binding_identifier() else {
            continue;
        };
        if !declarator.init.as_ref().is_some_and(is_function_expression) {
            continue;
        }
        spans.push(UnitSpan {
            name: identifier.name.to_string(),
            start: if position == 0 {
                declaration.span.start
            } else {
                declarator.span.start
            },
            end: declarator.span.end,
        });
    }
    spans
}

fn is_function_expression(expression: &Expression<'_>) -> bool {
    matches!(
        expression.without_parentheses(),
        Expression::ArrowFunctionExpression(_) | Expression::FunctionExpression(_)
    )
}

impl SyntaxMarks {
    fn callee(&mut self, callee: &Expression<'_>) {
        match callee.without_parentheses() {
            Expression::Identifier(identifier) => {
                self.call_targets.insert(identifier.span.start);
            }
            Expression::StaticMemberExpression(member) => {
                self.call_targets.insert(member.property.span.start);
            }
            Expression::PrivateFieldExpression(member) => {
                self.call_targets.insert(member.field.span.start);
            }
            _ => {}
        }
    }
}

impl<'a> Visit<'a> for SyntaxMarks {
    fn visit_identifier_name(&mut self, it: &IdentifierName<'a>) {
        self.names.insert(it.span.start);
    }

    fn visit_identifier_reference(&mut self, it: &IdentifierReference<'a>) {
        self.names.insert(it.span.start);
    }

    fn visit_binding_identifier(&mut self, it: &BindingIdentifier<'a>) {
        self.names.insert(it.span.start);
    }

    fn visit_label_identifier(&mut self, it: &LabelIdentifier<'a>) {
        self.names.insert(it.span.start);
    }

    fn visit_private_identifier(&mut self, it: &PrivateIdentifier<'a>) {
        self.names.insert(it.span.start);
    }

    fn visit_call_expression(&mut self, it: &CallExpression<'a>) {
        self.callee(&it.callee);
        walk::walk_call_expression(self, it);
    }

    fn visit_new_expression(&mut self, it: &NewExpression<'a>) {
        self.callee(&it.callee);
        walk::walk_new_expression(self, it);
    }

    fn visit_ts_type_annotation(&mut self, it: &TSTypeAnnotation<'a>) {
        self.ignored.push(it.span());
    }

    fn visit_ts_type_parameter_declaration(&mut self, it: &TSTypeParameterDeclaration<'a>) {
        self.ignored.push(it.span());
    }
}
