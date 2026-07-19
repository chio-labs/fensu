//! Parse one Python expression, rejecting any syntax error for the target version.

use ruff_python_ast::{ModExpression, PythonVersion};
use ruff_python_parser::{parse_unchecked, Mode, ParseOptions, Parsed};

use crate::parsing::helpers::failures;
use crate::parsing::models::ParseFailure;

/// Return the parsed expression or the earliest failure CPython would report.
pub fn parse_expression_strict(
    source: &str,
    version: PythonVersion,
) -> Result<Parsed<ModExpression>, ParseFailure> {
    let options = ParseOptions::from(Mode::Expression).with_target_version(version);
    let parsed = parse_unchecked(source, options);
    let Some(expression) = parsed.try_into_expression() else {
        return Err(failures::not_a_module_failure());
    };
    match failures::earliest_failure(source, &expression) {
        Some(failure) => Err(failure),
        None => Ok(expression),
    }
}
