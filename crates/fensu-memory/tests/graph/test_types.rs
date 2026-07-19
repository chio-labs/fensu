//! Test-case and fixture declarations for memory graph behavior.

use fensu_memory::graph::types::{DependencyState, GraphDiagnosticKind, ResolutionStatus};

pub(crate) struct FixtureFile {
    pub(crate) path: &'static str,
    pub(crate) contents: &'static str,
}

pub(crate) struct ExpectedResolvedLink {
    pub(crate) ordinal: usize,
    pub(crate) authored_target: &'static str,
    pub(crate) expected_status: ResolutionStatus,
    pub(crate) expected_target_identity: Option<&'static str>,
    pub(crate) expected_section_ordinal: Option<usize>,
}

pub(crate) struct ExpectedGraphDiagnostic {
    pub(crate) source_link_ordinal: Option<usize>,
    pub(crate) expected_kind: GraphDiagnosticKind,
}

pub(crate) struct LinkResolutionTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_source_identity: &'static str,
    pub(crate) expected_block_fragment: &'static str,
    pub(crate) expected_links: &'static [ExpectedResolvedLink],
    pub(crate) expected_diagnostics: &'static [ExpectedGraphDiagnostic],
}

pub(crate) struct ExpectedDependencyEdge {
    pub(crate) source_identity: &'static str,
    pub(crate) ordinal: usize,
    pub(crate) expected_target_identity: Option<&'static str>,
    pub(crate) expected_state: DependencyState,
}

pub(crate) struct DependencyGraphTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_edges: &'static [ExpectedDependencyEdge],
    pub(crate) expected_dependency_diagnostics: &'static [GraphDiagnosticKind],
    pub(crate) expected_cycle_identities: &'static [&'static str],
}
