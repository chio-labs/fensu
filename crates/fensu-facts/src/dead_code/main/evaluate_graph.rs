//! Apply the native reachability policy to an extracted graph snapshot.

use crate::dead_code::models::{GraphFacts, Root};

pub fn evaluate_graph(facts: &GraphFacts, roots: &[Root]) -> (Vec<usize>, Vec<usize>) {
    crate::dead_code::_helpers::graph::evaluate_graph(facts, roots)
}
