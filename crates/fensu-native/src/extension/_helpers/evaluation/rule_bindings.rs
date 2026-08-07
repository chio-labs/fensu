//! Python bindings for batched native core-rule evaluation.

use fensu_facts::extension::models::ProgramHandle;
use fensu_facts::facts::types::FactFamily;
use pyo3::exceptions::PyValueError;
use pyo3::{pyclass, pyfunction, Bound, Py, PyResult, Python};
use rayon::iter::{
    IndexedParallelIterator, IntoParallelIterator, IntoParallelRefIterator, ParallelIterator,
};
use ruff_python_ast::PythonVersion;
use std::collections::HashMap;

use crate::rules::constants::NATIVE_RULE_FACT_FAMILIES;
use crate::rules::main::evaluate_core_rules::evaluate_core_rules;
use crate::rules::main::plan_core_rule_queries::plan_core_rule_queries;
use crate::rules::models::{
    NativeFaultRow, NativeProjectModule, NativeProjectPlane, NativeRuleContext,
};

type NativeFaultTuple = (
    String,
    Option<String>,
    Option<u32>,
    Option<u32>,
    Option<String>,
    Option<String>,
);
type NativeProjectContextTuple = (
    Vec<String>,
    Vec<(String, String)>,
    HashMap<String, Vec<String>>,
    Vec<(String, String, String, String, u32, u32)>,
    String,
    HashMap<String, HashMap<String, String>>,
    Vec<String>,
);

type NativeProjectQueryTuple = (String, String, String, String);
type NativeProjectFileTuple = (String, String, Vec<String>, String);

type NativeRuleContextTuple = (
    String,
    Vec<String>,
    String,
    Option<String>,
    bool,
    HashMap<String, u32>,
    String,
    Vec<(String, String)>,
    Vec<String>,
    bool,
    String,
    NativeProjectContextTuple,
);

struct NativeExecutionRequest {
    program: ProgramHandle,
    codes: Vec<String>,
    context: NativeRuleContext,
}

struct ExecutionBatchPlanRequest<'py> {
    py: Python<'py>,
    requests: Vec<NativeRuleContextTuple>,
    project_files: Vec<NativeProjectFileTuple>,
    entrypoint_modules: Vec<String>,
    major: u8,
    minor: u8,
}

#[pyclass(frozen, module = "fensu._native")]
pub(crate) struct NativeExecutionBatch {
    requests: Vec<Option<NativeExecutionRequest>>,
    project: NativeProjectPlane,
}

type NativeExecutionPlanTuple = (
    Py<NativeExecutionBatch>,
    Vec<Vec<NativeProjectQueryTuple>>,
    Vec<usize>,
);

macro_rules! define_execution_plan_binding {
    () => {
        #[pyfunction]
        pub(crate) fn plan_native_execution_batch(
            py: Python<'_>,
            requests: Vec<NativeRuleContextTuple>,
            project_files: Vec<NativeProjectFileTuple>,
            entrypoint_modules: Vec<String>,
            major: u8,
            minor: u8,
        ) -> PyResult<NativeExecutionPlanTuple> {
            plan_execution_batch(ExecutionBatchPlanRequest {
                py,
                requests,
                project_files,
                entrypoint_modules,
                major,
                minor,
            })
        }
    };
}

define_execution_plan_binding!();

fn plan_execution_batch(
    request: ExecutionBatchPlanRequest<'_>,
) -> PyResult<NativeExecutionPlanTuple> {
    let ExecutionBatchPlanRequest {
        py,
        requests,
        project_files,
        entrypoint_modules,
        major,
        minor,
    } = request;
    let version = PythonVersion { major, minor };
    let (batch, plans, failures) = py.detach(move || {
        let sources: Vec<String> = requests.iter().map(|request| request.0.clone()).collect();
        let programs = ProgramHandle::parse_many(sources, version);
        let mut prepared = Vec::with_capacity(requests.len());
        for (program, request) in programs.into_iter().zip(requests) {
            prepared.push(program.map(|program| NativeExecutionRequest {
                program,
                codes: request.1,
                context: NativeRuleContext {
                    scope: request.2,
                    role: request.3,
                    is_main_module: request.4,
                    thresholds: request.5,
                    repository_path: request.6,
                    contracts: request.7,
                    relative_parts: request.8,
                    is_entry_module: request.9,
                    package_name: request.10,
                    tooling_packages: request.11 .0,
                    scope_roots: request.11 .1,
                    observations: request.11 .2,
                    custom_registrations: request.11 .3,
                    repo_root: request.11 .4,
                    rule_options: request.11 .5,
                    test_scopes: request.11 .6,
                },
            }));
        }
        let plans: Vec<Vec<NativeProjectQueryTuple>> =
            prepared.par_iter().map(plan_request_queries).collect();
        let failures: Vec<usize> = prepared
            .iter()
            .enumerate()
            .filter_map(|(index, request)| request.is_none().then_some(index))
            .collect();
        let request_programs: HashMap<String, ProgramHandle> =
            prepared.iter().filter_map(request_program).collect();
        let missing_sources: Vec<String> = project_files
            .iter()
            .filter(|(path, _, _, _)| !request_programs.contains_key(path))
            .map(|(_, _, _, source)| source.clone())
            .collect();
        let mut parsed_missing = ProgramHandle::parse_many(missing_sources, version).into_iter();
        let project_programs: Vec<Option<ProgramHandle>> = project_files
            .iter()
            .map(|(path, _, _, _)| {
                request_programs
                    .get(path)
                    .cloned()
                    .map(Some)
                    .unwrap_or_else(|| parsed_missing.next().flatten())
            })
            .collect();
        let mut modules: Vec<NativeProjectModule> = Vec::new();
        for ((path, scope, module_parts, _), program) in
            project_files.into_iter().zip(project_programs)
        {
            if let Some(program) = program {
                modules.push(NativeProjectModule {
                    path,
                    scope,
                    module_parts,
                    program,
                });
            }
        }
        (
            NativeExecutionBatch {
                requests: prepared,
                project: NativeProjectPlane {
                    modules,
                    entrypoint_modules,
                },
            },
            plans,
            failures,
        )
    });
    Ok((Py::new(py, batch)?, plans, failures))
}

#[pyfunction]
pub(crate) fn evaluate_native_execution_batch(
    py: Python<'_>,
    batch: &Bound<'_, NativeExecutionBatch>,
    observations: Vec<HashMap<String, Vec<String>>>,
) -> PyResult<Vec<Vec<NativeFaultTuple>>> {
    let batch = batch.get();
    py.detach(|| {
        batch
            .requests
            .par_iter()
            .zip(observations.into_par_iter())
            .map(|(request, observations)| evaluate_request(request, observations, &batch.project))
            .collect::<Result<Vec<_>, String>>()
            .map_err(PyValueError::new_err)
    })
}

#[pyfunction]
pub(crate) fn native_execution_programs(
    py: Python<'_>,
    batch: &Bound<'_, NativeExecutionBatch>,
) -> PyResult<Vec<Option<Py<ProgramHandle>>>> {
    batch
        .get()
        .requests
        .iter()
        .map(|request| execution_program(py, request))
        .collect()
}

fn extract_required_rows(program: &ProgramHandle, codes: &[String]) {
    let selected: std::collections::HashSet<&str> = codes.iter().map(String::as_str).collect();
    for (code, families) in NATIVE_RULE_FACT_FAMILIES {
        if !selected.contains(code) {
            continue;
        }
        for family in *families {
            if let Some(family) = fact_family(family) {
                program.extract_rows(family);
            }
        }
    }
}

fn fact_family(name: &str) -> Option<FactFamily> {
    match name {
        "annotations" => Some(FactFamily::Annotations),
        "assignment_references" => Some(FactFamily::AssignmentReferences),
        "class_declarations" => Some(FactFamily::ClassDeclarations),
        "comments" => Some(FactFamily::Comments),
        "complex_comprehensions" | "function_conditionals" => Some(FactFamily::ControlFlow),
        "comparisons" => Some(FactFamily::Comparisons),
        "dataclasses" => Some(FactFamily::Dataclasses),
        "function_contracts" => Some(FactFamily::Contracts),
        "functions" => Some(FactFamily::Functions),
        "hygiene" => Some(FactFamily::Hygiene),
        "local_call_edges" => Some(FactFamily::LocalCallEdges),
        "module_declarations" => Some(FactFamily::Declarations),
        "named_calls" => Some(FactFamily::NamedCalls),
        "outer_state_mutations" => Some(FactFamily::OuterStateMutations),
        "parameter_mutation_occurrences" => Some(FactFamily::ParameterMutationOccurrences),
        "parameter_mutations" => Some(FactFamily::ParameterMutations),
        "project_calls" | "project_functions" => Some(FactFamily::Project),
        "references" => Some(FactFamily::References),
        "test_functions" => Some(FactFamily::TestFunctions),
        "test_module" => Some(FactFamily::TestModule),
        _ => None,
    }
}

#[pyfunction]
pub(crate) fn native_rule_fact_families() -> Vec<(String, Vec<String>)> {
    NATIVE_RULE_FACT_FAMILIES
        .iter()
        .map(|(code, families)| ((*code).to_owned(), owned_families(families)))
        .collect()
}

#[pyfunction]
pub(crate) fn native_generated_policy_owners() -> Vec<String> {
    crate::rules::main::generated_policy_owners::generated_policy_owners()
        .iter()
        .map(|code| (*code).to_owned())
        .collect()
}

fn plan_request_queries(request: &Option<NativeExecutionRequest>) -> Vec<NativeProjectQueryTuple> {
    let Some(request) = request else {
        return Vec::new();
    };
    plan_core_rule_queries(&request.program, &request.codes, &request.context)
        .into_iter()
        .map(|query| (query.key(), query.kind, query.path, query.argument))
        .collect()
}

fn request_program(request: &Option<NativeExecutionRequest>) -> Option<(String, ProgramHandle)> {
    request.as_ref().map(|request| {
        (
            request.context.repository_path.clone(),
            request.program.clone(),
        )
    })
}

fn evaluate_request(
    request: &Option<NativeExecutionRequest>,
    observations: HashMap<String, Vec<String>>,
    project: &NativeProjectPlane,
) -> Result<Vec<NativeFaultTuple>, String> {
    let Some(request) = request else {
        return Ok(Vec::new());
    };
    let mut context = request.context.clone();
    context.observations = observations;
    extract_required_rows(&request.program, &request.codes);
    let rows = evaluate_core_rules(&request.program, &request.codes, &context, project)?;
    Ok(rows.into_iter().map(as_tuple).collect())
}

fn execution_program(
    py: Python<'_>,
    request: &Option<NativeExecutionRequest>,
) -> PyResult<Option<Py<ProgramHandle>>> {
    request
        .as_ref()
        .map(|request| Py::new(py, request.program.clone()))
        .transpose()
}

fn owned_families(families: &[&str]) -> Vec<String> {
    families.iter().map(|family| (*family).to_owned()).collect()
}

fn as_tuple(row: NativeFaultRow) -> NativeFaultTuple {
    let location = (row.line != 0).then_some((row.line, row.column));
    (
        row.code,
        row.path,
        location.map(|(line, _)| line),
        location.map(|(_, column)| column),
        row.message,
        row.remediation,
    )
}
