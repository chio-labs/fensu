//! A parsed-program handle shared by native fact-family bindings.

use pyo3::pyclass;
use ruff_python_ast::token::Tokens;
use ruff_python_ast::{ModModule, PythonVersion};
use ruff_python_parser::Parsed;

use crate::parsing::main::parse_strict::parse_strict;
use crate::parsing::models::ParseFailure;
use crate::positions::main::index_lines::index_lines;
use crate::positions::models::LineIndex;

/// One parsed Python module retained for repeated fact extraction.
#[pyclass(frozen, module = "strata_facts")]
pub(crate) struct ProgramHandle {
    source: String,
    parsed: Parsed<ModModule>,
    index: LineIndex,
    version: PythonVersion,
}

impl ProgramHandle {
    pub(crate) fn parse(source: &str, version: PythonVersion) -> Result<Self, ParseFailure> {
        let parsed = parse_strict(source, version)?;
        Ok(Self {
            source: source.to_owned(),
            parsed,
            index: index_lines(source),
            version,
        })
    }

    pub(crate) fn source(&self) -> &str {
        &self.source
    }

    pub(crate) fn module(&self) -> &ModModule {
        self.parsed.syntax()
    }

    pub(crate) fn tokens(&self) -> &Tokens {
        self.parsed.tokens()
    }

    pub(crate) fn index(&self) -> &LineIndex {
        &self.index
    }

    pub(crate) fn version(&self) -> PythonVersion {
        self.version
    }
}
