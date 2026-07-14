//! Compute CPython-convention spans for shaped nodes.

use ruff_python_ast::Stmt;
use ruff_text_size::{Ranged, TextRange};

use crate::constants;
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::positions::models::LineIndex;

pub(crate) fn span(
    node: &ShapeNode<'_>,
    index: &LineIndex,
    source: &str,
) -> Option<(u32, u32, u32, u32)> {
    let range = match node {
        ShapeNode::Module(_)
        | ShapeNode::Parameters(_)
        | ShapeNode::EmptyParameters
        | ShapeNode::Comprehension(_)
        | ShapeNode::MatchCase(_)
        | ShapeNode::WithItem(_) => return None,
        ShapeNode::Stmt(statement) => statement_range(statement, source),
        ShapeNode::IfTail(clauses) => {
            let first = clauses.first()?;
            let last = clauses.last()?;
            TextRange::new(first.range().start(), last.range().end())
        }
        ShapeNode::Expr(expression) => expression.range(),
        ShapeNode::GeneratorInCall(_, arguments_range) => *arguments_range,
        ShapeNode::Parameter(parameter) => parameter_range(parameter, source),
        ShapeNode::Keyword(keyword) => keyword.range(),
        ShapeNode::ExceptHandler(handler) => handler.range(),
        ShapeNode::Alias(alias) => alias.range(),
        ShapeNode::Pattern(pattern) => pattern.range(),
        ShapeNode::TypeParam(type_param) => type_param.range(),
        ShapeNode::FormattedValue(element) => element.range(),
        ShapeNode::FStringLiteral(range) => *range,
        ShapeNode::FormatSpec(format_spec) => {
            let start = format_spec.range().start().to_usize().saturating_sub(1);
            let end = format_spec.range().end().to_usize();
            return Some(span_from_offsets(index, start, end));
        }
    };
    Some(span_from_offsets(
        index,
        range.start().to_usize(),
        range.end().to_usize(),
    ))
}

pub(crate) fn start_of(node: &ShapeNode<'_>, index: &LineIndex, source: &str) -> (u32, u32) {
    match span(node, index, source) {
        Some((line, column, _, _)) => (line, column),
        None => (1, 0),
    }
}

fn span_from_offsets(index: &LineIndex, start: usize, end: usize) -> (u32, u32, u32, u32) {
    let start_location = index.locate(start);
    let end_location = index.locate(end);
    (
        start_location.line,
        start_location.column,
        end_location.line,
        end_location.column,
    )
}

fn statement_range(statement: &Stmt, source: &str) -> TextRange {
    match statement {
        Stmt::FunctionDef(inner) => definition_range(
            inner.range(),
            inner
                .decorator_list
                .last()
                .map(|decorator| decorator.range()),
            source,
        ),
        Stmt::ClassDef(inner) => definition_range(
            inner.range(),
            inner
                .decorator_list
                .last()
                .map(|decorator| decorator.range()),
            source,
        ),
        _ => statement.range(),
    }
}

fn definition_range(
    range: TextRange,
    last_decorator: Option<TextRange>,
    source: &str,
) -> TextRange {
    let Some(decorator_range) = last_decorator else {
        return range;
    };
    let keyword_start = keyword_start_after(source, decorator_range.end().to_usize());
    let clamped = keyword_start.min(range.end().to_usize());
    let Ok(start) = u32::try_from(clamped) else {
        return range;
    };
    TextRange::new(start.into(), range.end())
}

fn parameter_range(parameter: &ruff_python_ast::Parameter, source: &str) -> TextRange {
    let name_range = parameter.name.range();
    let Some(annotation) = parameter.annotation.as_deref() else {
        return name_range;
    };
    let annotation_range = annotation.range();
    let open_count = unmatched_open_parens(
        source,
        name_range.end().to_usize(),
        annotation_range.start().to_usize(),
    );
    let extended = end_after_closing_parens(source, annotation_range.end().to_usize(), open_count);
    let Ok(end) = u32::try_from(extended) else {
        return TextRange::new(name_range.start(), annotation_range.end());
    };
    TextRange::new(name_range.start(), end.into())
}

fn unmatched_open_parens(source: &str, from: usize, until: usize) -> usize {
    let bytes = source.as_bytes();
    let mut offset = from;
    let mut depth: usize = 0;
    while offset < until.min(bytes.len()) {
        match bytes[offset] {
            byte if byte == constants::COMMENT_BYTE => {
                while offset < bytes.len() && bytes[offset] != constants::NEWLINE_BYTE {
                    offset += 1;
                }
            }
            byte if byte == constants::OPEN_PAREN_BYTE => {
                depth += 1;
                offset += 1;
            }
            byte if byte == constants::CLOSE_PAREN_BYTE => {
                depth = depth.saturating_sub(1);
                offset += 1;
            }
            _ => offset += 1,
        }
    }
    depth
}

fn end_after_closing_parens(source: &str, from: usize, count: usize) -> usize {
    let bytes = source.as_bytes();
    let mut offset = from;
    let mut remaining = count;
    let mut end = from;
    while remaining > 0 && offset < bytes.len() {
        let byte = bytes[offset];
        if byte == constants::COMMENT_BYTE {
            while offset < bytes.len() && bytes[offset] != constants::NEWLINE_BYTE {
                offset += 1;
            }
            continue;
        }
        if byte == constants::CLOSE_PAREN_BYTE {
            offset += 1;
            end = offset;
            remaining -= 1;
            continue;
        }
        if byte.is_ascii_whitespace() {
            offset += 1;
            continue;
        }
        break;
    }
    end
}

fn keyword_start_after(source: &str, from: usize) -> usize {
    let bytes = source.as_bytes();
    let mut offset = from;
    while offset < bytes.len() {
        let byte = bytes[offset];
        if byte == constants::COMMENT_BYTE {
            while offset < bytes.len() && bytes[offset] != constants::NEWLINE_BYTE {
                offset += 1;
            }
            continue;
        }
        if byte.is_ascii_whitespace() {
            offset += 1;
            continue;
        }
        break;
    }
    offset
}
