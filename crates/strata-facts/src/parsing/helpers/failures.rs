//! Convert parser diagnostics into position-resolved parse failures.

use ruff_python_ast::ModModule;
use ruff_python_parser::Parsed;

use crate::parsing::models::ParseFailure;
use crate::positions::main::locate_offset::locate_offset;

pub(crate) fn earliest_failure(source: &str, parsed: &Parsed<ModModule>) -> Option<ParseFailure> {
    let mut candidates: Vec<(usize, String)> = Vec::new();
    for error in parsed.errors() {
        candidates.push((error.location.start().to_usize(), error.error.to_string()));
    }
    for error in parsed.unsupported_syntax_errors() {
        candidates.push((error.range.start().to_usize(), error.to_string()));
    }
    candidates.sort_by(|left, right| left.0.cmp(&right.0).then_with(|| left.1.cmp(&right.1)));
    let (offset, message) = candidates.into_iter().next()?;
    let location = locate_offset(source, offset);
    Some(ParseFailure {
        line: location.line,
        column: location.column,
        message,
    })
}

pub(crate) fn not_a_module_failure() -> ParseFailure {
    ParseFailure {
        line: 1,
        column: 0,
        message: "source did not parse as a module".to_owned(),
    }
}
