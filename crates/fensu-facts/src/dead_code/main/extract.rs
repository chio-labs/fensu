//! Extract declarations and resolved dependencies without evaluating liveness.

use crate::dead_code::models::{GraphFacts, Module, ProjectEntryPoint};

pub fn extract(modules: &[Module], entries: &[ProjectEntryPoint]) -> GraphFacts {
    crate::dead_code::_helpers::graph::extract(modules, entries)
}
