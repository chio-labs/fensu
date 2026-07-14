//! Python-callable bindings over native domain entries.

use pyo3::pyfunction;

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
