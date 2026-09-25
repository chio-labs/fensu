//! Analyze the caller's already-selected production modules.

use crate::dead_code::models::{Analysis, Module, ProjectEntryPoint, Root};

pub fn analyze(modules: &[Module], entries: &[ProjectEntryPoint], roots: &[Root]) -> Analysis {
    crate::dead_code::_helpers::graph::analyze(modules, entries, roots)
}
