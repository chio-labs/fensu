//! The Python version used for parsing.

use ruff_python_ast::PythonVersion;

pub(crate) fn python_version() -> PythonVersion {
    crate::check::_helpers::policy::python_version()
}
