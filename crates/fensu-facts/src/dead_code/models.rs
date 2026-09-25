//! Inputs and findings for target-local Python reachability.

use crate::extension::models::ProgramHandle;

#[derive(Clone, Debug)]
pub struct Module {
    pub name: String,
    pub program: ProgramHandle,
    /// Root-package initializer, whose public bindings form its API.
    pub package: bool,
    /// Any package initializer, including a nested package.
    pub initializer: bool,
}

#[derive(Clone, Debug)]
pub struct Root {
    pub modules: Vec<String>,
    pub symbols: Vec<String>,
}

#[derive(Clone, Debug)]
pub struct Declaration {
    pub module: usize,
    /// Empty for a module-execution node; local closures have their own nodes.
    pub name: String,
    pub kind: &'static str,
    pub line: u32,
    pub column: u32,
}

#[derive(Clone, Debug, Default)]
pub struct Analysis {
    pub dead: Vec<Declaration>,
    pub stale_roots: Vec<usize>,
}

#[derive(Clone, Debug)]
pub struct ProjectEntryPoint {
    pub kind: String,
    pub reference: String,
}

#[derive(Clone, Debug)]
pub struct EntryPointFact {
    pub node: Option<usize>,
    pub kind: String,
    pub reference: String,
}

#[derive(Clone, Debug)]
pub struct GraphFacts {
    pub modules: Vec<String>,
    pub declarations: Vec<Declaration>,
    pub references: Vec<(usize, usize)>,
    pub entrypoints: Vec<EntryPointFact>,
}
