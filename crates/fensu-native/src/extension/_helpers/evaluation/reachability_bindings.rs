//! Project-level Python facts, without policy evaluation or liveness verdicts.

use fensu_facts::dead_code::main::extract::extract;
use fensu_facts::dead_code::models::{
    Declaration, EntryPointFact, GraphFacts, Module, ProjectEntryPoint, Root,
};
use fensu_facts::extension::models::ProgramHandle;
use globset::Glob;
use pyo3::exceptions::PyValueError;
use pyo3::{pyfunction, PyResult, Python};
use ruff_python_ast::PythonVersion;

type ModuleInput = (String, String, bool, bool);
type DeclarationRow = (usize, String, String, u32, u32);
type EntryPointRow = (Option<usize>, String, String);
type GraphRows = (Vec<DeclarationRow>, Vec<(usize, usize)>, Vec<EntryPointRow>);
type PolicyGraph = (
    Vec<String>,
    Vec<(usize, String, bool)>,
    Vec<(usize, usize)>,
    Vec<usize>,
);

#[pyfunction]
pub(crate) fn evaluate_python_reachability(
    graph: PolicyGraph,
    roots: Vec<(Vec<String>, Vec<String>)>,
) -> PyResult<(Vec<usize>, Vec<usize>)> {
    let (modules, declarations, references, entrypoints) = graph;
    if declarations
        .iter()
        .any(|(module, _, _)| *module >= modules.len())
        || references
            .iter()
            .any(|(source, target)| *source >= declarations.len() || *target >= declarations.len())
        || entrypoints.iter().any(|node| *node >= declarations.len())
    {
        return Err(PyValueError::new_err(
            "Reachability graph contains an invalid node or module identity.",
        ));
    }
    let facts = GraphFacts {
        modules,
        declarations: declarations
            .into_iter()
            .map(|(module, name, local)| Declaration {
                module,
                name,
                kind: if local { "local" } else { "declaration" },
                line: 0,
                column: 0,
            })
            .collect(),
        references,
        entrypoints: entrypoints
            .into_iter()
            .map(|node| EntryPointFact {
                node: Some(node),
                kind: String::new(),
                reference: String::new(),
            })
            .collect(),
    };
    let roots = roots
        .into_iter()
        .map(|(modules, symbols)| Root { modules, symbols })
        .collect::<Vec<_>>();
    Ok(fensu_facts::dead_code::main::evaluate_graph::evaluate_graph(&facts, &roots))
}

#[pyfunction]
pub(crate) fn python_reachability_facts(
    py: Python<'_>,
    sources: Vec<ModuleInput>,
    entries: Vec<(String, String)>,
    version: (u8, u8),
) -> PyResult<GraphRows> {
    py.detach(move || {
        let programs = ProgramHandle::parse_many(
            sources.iter().map(|source| source.1.clone()).collect(),
            PythonVersion {
                major: version.0,
                minor: version.1,
            },
        );
        let mut modules: Vec<Module> = Vec::new();
        for ((name, _, package, initializer), program) in sources.into_iter().zip(programs) {
            let program = program.ok_or_else(|| {
                PyValueError::new_err(format!("Could not parse reachability source {name}."))
            })?;
            modules.push(Module {
                name,
                program,
                package,
                initializer,
            });
        }
        let entries = entries
            .into_iter()
            .map(|(kind, reference)| ProjectEntryPoint { kind, reference })
            .collect::<Vec<_>>();
        let facts = extract(&modules, &entries);
        Ok((
            facts
                .declarations
                .into_iter()
                .map(|node| {
                    (
                        node.module,
                        node.name,
                        node.kind.to_owned(),
                        node.line,
                        node.column,
                    )
                })
                .collect(),
            facts.references,
            facts
                .entrypoints
                .into_iter()
                .map(|entry| (entry.node, entry.kind, entry.reference))
                .collect(),
        ))
    })
}

#[pyfunction]
pub(crate) fn symbol_pattern_matches(value: &str, patterns: Vec<String>) -> PyResult<bool> {
    let mut matched = false;
    for pattern in patterns {
        let glob = Glob::new(&pattern).map_err(|error| PyValueError::new_err(error.to_string()))?;
        matched |= glob.compile_matcher().is_match(value);
    }
    Ok(matched)
}
