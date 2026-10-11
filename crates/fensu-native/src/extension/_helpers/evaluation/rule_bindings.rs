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

use crate::extension::_helpers::evaluation::python_rows::{
    FaultRow, ProjectFileRow, ProjectQueryRow, RuleContextRow,
};

struct NativeExecutionRequest {
    program: ProgramHandle,
    codes: Vec<String>,
    context: NativeRuleContext,
}

struct ExecutionBatchPlanRequest<'py> {
    py: Python<'py>,
    requests: Vec<RuleContextRow>,
    project_files: Vec<ProjectFileRow>,
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
    Vec<Vec<ProjectQueryRow>>,
    Vec<usize>,
);

macro_rules! define_execution_plan_binding {
    () => {
        #[pyfunction]
        pub(crate) fn plan_native_execution_batch(
            py: Python<'_>,
            requests: Vec<RuleContextRow>,
            project_files: Vec<ProjectFileRow>,
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

#[pyfunction]
pub(crate) fn parse_dead_code_config(
    value: &str,
) -> PyResult<crate::rules::types::NativeDeadCodeSettings> {
    let value =
        serde_json::from_str(value).map_err(|error| PyValueError::new_err(error.to_string()))?;
    crate::rules::main::parse_dead_code::parse_dead_code(&value).map_err(PyValueError::new_err)
}

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
        let sources: Vec<String> = requests
            .iter()
            .map(|request| request.source.clone())
            .collect();
        let programs = ProgramHandle::parse_many(sources, version);
        let mut prepared = Vec::with_capacity(requests.len());
        for (program, request) in programs.into_iter().zip(requests) {
            prepared.push(program.map(|program| {
                NativeExecutionRequest {
                    program,
                    codes: request.codes,
                    context: NativeRuleContext {
                        dead_code: Default::default(),
                        scope: request.scope,
                        role: request.role,
                        is_main_module: request.is_main_module,
                        thresholds: request.thresholds,
                        repository_path: request.repository_path,
                        contracts: request.contracts,
                        relative_parts: request.relative_parts,
                        is_entry_module: request.is_entry_module,
                        package_name: request.package_name,
                        tooling_packages: request.project.tooling_packages,
                        scope_roots: request.project.scope_roots,
                        observations: request.project.observations,
                        custom_registrations: request
                            .project
                            .custom_registrations
                            .into_iter()
                            .map(Into::into)
                            .collect(),
                        repo_root: request.project.repo_root,
                        rule_options: request.project.rule_options,
                        test_scopes: request.project.test_scopes,
                        ownership_offset: request.project.ownership_offset,
                        ownership_root: request.project.ownership_root,
                        ownership_roots: request.project.ownership_roots,
                    },
                }
            }));
        }
        let plans: Vec<Vec<ProjectQueryRow>> =
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
            .filter(|file| !request_programs.contains_key(&file.path))
            .map(|file| file.source.clone())
            .collect();
        let mut parsed_missing = ProgramHandle::parse_many(missing_sources, version).into_iter();
        let project_programs: Vec<Option<ProgramHandle>> = project_files
            .iter()
            .map(|file| {
                request_programs
                    .get(&file.path)
                    .cloned()
                    .map(Some)
                    .unwrap_or_else(|| parsed_missing.next().flatten())
            })
            .collect();
        let mut modules: Vec<NativeProjectModule> = Vec::new();
        for (
            ProjectFileRow {
                path,
                scope,
                module_parts,
                source: _,
                ownership_start,
                ownership_root,
            },
            program,
        ) in project_files.into_iter().zip(project_programs)
        {
            if let Some(program) = program {
                modules.push(NativeProjectModule {
                    path,
                    scope,
                    module_parts,
                    program,
                    ownership_start,
                    ownership_root,
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
) -> PyResult<Vec<Vec<FaultRow>>> {
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

fn plan_request_queries(request: &Option<NativeExecutionRequest>) -> Vec<ProjectQueryRow> {
    let Some(request) = request else {
        return Vec::new();
    };
    plan_core_rule_queries(&request.program, &request.codes, &request.context)
        .into_iter()
        .map(|query| ProjectQueryRow {
            key: query.key(),
            kind: query.kind,
            path: query.path,
            argument: query.argument,
        })
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
) -> Result<Vec<FaultRow>, String> {
    let Some(request) = request else {
        return Ok(Vec::new());
    };
    let mut context = request.context.clone();
    context.observations = observations;
    extract_required_rows(&request.program, &request.codes);
    let rows = evaluate_core_rules(&request.program, &request.codes, &context, project)?;
    Ok(rows.into_iter().map(fault_row).collect())
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

fn fault_row(row: NativeFaultRow) -> FaultRow {
    let location = (row.line != 0).then_some((row.line, row.column));
    FaultRow {
        code: row.code,
        path: row.path,
        line: location.map(|(line, _)| line),
        column: location.map(|(_, column)| column),
        message: row.message,
        remediation: row.remediation,
    }
}
