//! Register the strata_facts Python module surface.

use pyo3::pymodule;
use pyo3::types::{PyModule, PyModuleMethods};
use pyo3::wrap_pyfunction;
use pyo3::{Bound, PyResult};

use crate::extension::helpers::gateway::bindings;
use crate::extension::helpers::gateway::program::ProgramHandle;

/// Expose the native fact-extraction functions to Python.
#[pymodule]
pub fn strata_facts(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(bindings::annotation_facts, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::backend_version, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::check_syntax, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::dataclass_facts, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::project_facts, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::list_syntax_nodes, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::comment_facts, module)?)?;
    module.add_function(wrap_pyfunction!(
        bindings::evaluate_rule_call_facts,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(bindings::function_contract_facts, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::function_facts, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::locate_byte_offset, module)?)?;
    module.add_function(wrap_pyfunction!(
        bindings::parameter_mutation_facts,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        bindings::module_declaration_facts,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        bindings::outer_state_mutation_facts,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(bindings::parse_program, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::reference_facts, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::test_function_facts, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::test_module_facts, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::hygiene_facts, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::control_flow_facts, module)?)?;
    module.add_class::<ProgramHandle>()?;
    Ok(())
}
