//! Named evaluation rows preserving positional Python input and output contracts.

use std::collections::HashMap;

use crate::rules::models::CustomRegistration;

macro_rules! python_tuple_row {
    ($name:ident { $($field:ident: $field_type:ty),+ $(,)? }) => {
        pub(crate) struct $name {
            $(pub(crate) $field: $field_type,)+
        }

        impl<'a, 'py> pyo3::FromPyObject<'a, 'py> for $name {
            type Error = pyo3::PyErr;

            fn extract(object: pyo3::Borrowed<'a, 'py, pyo3::PyAny>) -> pyo3::PyResult<Self> {
                let ($($field,)+) = object.extract()?;
                Ok(Self { $($field,)+ })
            }
        }

        impl<'py> pyo3::IntoPyObject<'py> for $name {
            type Target = pyo3::types::PyTuple;
            type Output = pyo3::Bound<'py, Self::Target>;
            type Error = pyo3::PyErr;

            fn into_pyobject(self, py: pyo3::Python<'py>) -> pyo3::PyResult<Self::Output> {
                ($(self.$field,)+).into_pyobject(py)
            }
        }
    };
}

python_tuple_row!(TargetRow {
    repository_path: String,
    scope: String,
    root: String,
    relative_parts: Vec<String>,
    direct: bool,
    ownership_root: Option<String>,
    ownership_offset: Option<usize>,
});
python_tuple_row!(ModuleInput {
    name: String,
    source: String,
    package: bool,
    initializer: bool,
});
python_tuple_row!(DeclarationRow {
    module: usize,
    name: String,
    kind: String,
    line: u32,
    column: u32,
});
python_tuple_row!(PolicyGraph {
    modules: Vec<String>,
    declarations: Vec<(usize, String, bool)>,
    references: Vec<(usize, usize)>,
    entrypoints: Vec<usize>,
});
python_tuple_row!(FaultRow {
    code: String,
    path: Option<String>,
    line: Option<u32>,
    column: Option<u32>,
    message: Option<String>,
    remediation: Option<String>,
});
python_tuple_row!(ProjectContextRow {
    tooling_packages: Vec<String>,
    scope_roots: Vec<(String, String)>,
    observations: HashMap<String, Vec<String>>,
    custom_registrations: Vec<RegistrationRow>,
    repo_root: String,
    rule_options: HashMap<String, HashMap<String, String>>,
    test_scopes: Vec<String>,
    ownership_offset: Option<usize>,
    ownership_root: Option<String>,
    ownership_roots: Vec<String>,
});
python_tuple_row!(RegistrationRow {
    code: String,
    module: String,
    name: String,
    source_path: String,
    line: u32,
    column: u32,
});
python_tuple_row!(ProjectQueryRow {
    key: String,
    kind: String,
    path: String,
    argument: String,
});
python_tuple_row!(ProjectFileRow {
    path: String,
    scope: String,
    module_parts: Vec<String>,
    source: String,
    ownership_start: Option<usize>,
    ownership_root: Option<String>,
});
python_tuple_row!(RuleContextRow {
    source: String,
    codes: Vec<String>,
    scope: String,
    role: Option<String>,
    is_main_module: bool,
    thresholds: HashMap<String, u32>,
    repository_path: String,
    contracts: Vec<(String, String)>,
    relative_parts: Vec<String>,
    is_entry_module: bool,
    package_name: String,
    project: ProjectContextRow,
});

impl From<RegistrationRow> for CustomRegistration {
    fn from(row: RegistrationRow) -> Self {
        Self {
            code: row.code,
            module: row.module,
            name: row.name,
            source_path: row.source_path,
            line: row.line,
            column: row.column,
        }
    }
}
