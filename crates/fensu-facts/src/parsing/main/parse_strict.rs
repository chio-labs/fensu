//! Parse one Python module, rejecting any syntax error for the target version.

use ruff_python_ast::{ModModule, PythonVersion};
use ruff_python_parser::{parse_unchecked, Mode, ParseOptions, Parsed};

use crate::parsing::helpers::failures;
use crate::parsing::models::ParseFailure;

/// Return the parsed module or the earliest failure CPython would report.
pub fn parse_strict(
    source: &str,
    version: PythonVersion,
) -> Result<Parsed<ModModule>, ParseFailure> {
    let options = ParseOptions::from(Mode::Module).with_target_version(version);
    let parsed = parse_unchecked(source, options);
    let Some(module) = parsed.try_into_module() else {
        return Err(failures::not_a_module_failure());
    };
    match failures::earliest_failure(source, &module) {
        Some(failure) => Err(failure),
        None => Ok(module),
    }
}
