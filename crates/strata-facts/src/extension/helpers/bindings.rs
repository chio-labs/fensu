//! Python-callable bindings over native domain entries.

use pyo3::pyfunction;
use ruff_python_ast::PythonVersion;

use crate::parsing::main::parse_strict::parse_strict;
use crate::positions::main::locate_offset::locate_offset;

#[pyfunction]
pub(crate) fn backend_version() -> String {
    env!("CARGO_PKG_VERSION").to_owned()
}

#[pyfunction]
pub(crate) fn locate_byte_offset(source: &str, offset: usize) -> (u32, u32) {
    let location = locate_offset(source, offset);
    (location.line, location.column)
}

#[pyfunction]
pub(crate) fn check_syntax(source: &str, major: u8, minor: u8) -> Option<(u32, u32, String)> {
    let version = PythonVersion { major, minor };
    match parse_strict(source, version) {
        Ok(_) => None,
        Err(failure) => Some((failure.line, failure.column, failure.message)),
    }
}
