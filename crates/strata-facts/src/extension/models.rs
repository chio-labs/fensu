//! Parsed-program state shared by native fact-family bindings and rule kernels.

use std::sync::OnceLock;

use pyo3::pyclass;
use rayon::iter::{IntoParallelIterator, ParallelIterator};
use ruff_python_ast::token::Tokens;
use ruff_python_ast::{ModModule, PythonVersion};
use ruff_python_parser::Parsed;

use crate::facts::main::extract_annotations::extract_annotations;
use crate::facts::main::extract_class_declarations::extract_class_declarations;
use crate::facts::main::extract_comments::extract_comments;
use crate::facts::main::extract_control_flow::extract_control_flow;
use crate::facts::main::extract_dataclasses::extract_dataclasses;
use crate::facts::main::extract_function_contracts::extract_function_contracts;
use crate::facts::main::extract_functions::extract_functions;
use crate::facts::main::extract_hygiene::extract_hygiene;
use crate::facts::main::extract_module_declarations::extract_module_declarations;
use crate::facts::main::extract_outer_state_mutations::extract_outer_state_mutations;
use crate::facts::main::extract_parameter_mutation_occurrences::extract_parameter_mutation_occurrences;
use crate::facts::main::extract_parameter_mutations::extract_parameter_mutations;
use crate::facts::main::extract_references::extract_references;
use crate::facts::main::extract_rule_calls::extract_rule_calls;
use crate::facts::main::extract_rule_references::extract_rule_references;
use crate::facts::main::extract_test_functions::extract_test_functions;
use crate::facts::main::extract_test_module::extract_test_module;
use crate::facts::models::{
    AnnotationRows, AssignmentReferenceRow, ClassDeclarationRow, CommentRow, ComparisonRow,
    ControlFlowRows, DataclassRow, FunctionContractRow, FunctionMetricRow, HygieneRows,
    LocalCallEdgeRow, ModuleDeclarationRows, ParameterMutationOccurrenceRow, ParameterMutationRow,
    ReferenceRows, RuleNamedCallRow, SourceRangeRow, TestFunctionRow, TestModuleRows,
};
use crate::facts::types::FactFamily;
use crate::parsing::main::parse_strict::parse_strict;
use crate::parsing::models::ParseFailure;
use crate::positions::main::index_lines::index_lines;
use crate::positions::models::LineIndex;

/// Extracted fact rows cached once per parsed program.
#[derive(Debug, Default)]
struct FactRowCache {
    annotations: OnceLock<AnnotationRows>,
    class_declarations: OnceLock<Vec<ClassDeclarationRow>>,
    comments: OnceLock<Vec<CommentRow>>,
    contracts: OnceLock<Vec<FunctionContractRow>>,
    control_flow: OnceLock<ControlFlowRows>,
    dataclasses: OnceLock<Vec<DataclassRow>>,
    declarations: OnceLock<ModuleDeclarationRows>,
    functions: OnceLock<(Vec<FunctionMetricRow>, Vec<usize>)>,
    hygiene: OnceLock<HygieneRows>,
    rule_calls: OnceLock<(Vec<RuleNamedCallRow>, Vec<LocalCallEdgeRow>)>,
    rule_references: OnceLock<(Vec<AssignmentReferenceRow>, Vec<ComparisonRow>)>,
    outer_state_mutations: OnceLock<Vec<SourceRangeRow>>,
    parameter_mutation_occurrences: OnceLock<Vec<ParameterMutationOccurrenceRow>>,
    parameter_mutations: OnceLock<Vec<ParameterMutationRow>>,
    references: OnceLock<ReferenceRows>,
    test_functions: OnceLock<Vec<TestFunctionRow>>,
    test_module: OnceLock<TestModuleRows>,
}

/// One parsed Python module retained for repeated fact extraction.
#[pyclass(frozen, module = "strata._native")]
#[derive(Debug)]
pub struct ProgramHandle {
    source: String,
    parsed: Parsed<ModModule>,
    index: LineIndex,
    version: PythonVersion,
    rows: FactRowCache,
}

impl ProgramHandle {
    pub(crate) fn parse(source: &str, version: PythonVersion) -> Result<Self, ParseFailure> {
        let parsed = parse_strict(source, version)?;
        Ok(Self {
            source: source.to_owned(),
            parsed,
            index: index_lines(source),
            version,
            rows: FactRowCache::default(),
        })
    }

    pub(crate) fn parse_many(sources: Vec<String>, version: PythonVersion) -> Vec<Option<Self>> {
        sources
            .into_par_iter()
            .map(|source| Self::parse(&source, version).ok())
            .collect()
    }

    pub(crate) fn source(&self) -> &str {
        &self.source
    }

    pub(crate) fn module(&self) -> &ModModule {
        self.parsed.syntax()
    }

    pub(crate) fn tokens(&self) -> &Tokens {
        self.parsed.tokens()
    }

    pub(crate) fn index(&self) -> &LineIndex {
        &self.index
    }

    pub(crate) fn version(&self) -> PythonVersion {
        self.version
    }

    pub fn annotation_rows(&self) -> &AnnotationRows {
        self.rows
            .annotations
            .get_or_init(|| extract_annotations(self.module(), self.index(), self.source()))
    }

    pub(crate) fn assignment_reference_rows(&self) -> &[AssignmentReferenceRow] {
        &self
            .rows
            .rule_references
            .get_or_init(|| extract_rule_references(self.module(), self.index(), self.source()))
            .0
    }

    pub fn comment_rows(&self) -> &[CommentRow] {
        self.rows
            .comments
            .get_or_init(|| extract_comments(self.tokens(), self.source(), self.index()))
    }

    pub(crate) fn class_declaration_rows(&self) -> &[ClassDeclarationRow] {
        self.rows
            .class_declarations
            .get_or_init(|| extract_class_declarations(self.module(), self.index(), self.source()))
    }

    pub(crate) fn comparison_rows(&self) -> &[ComparisonRow] {
        &self
            .rows
            .rule_references
            .get_or_init(|| extract_rule_references(self.module(), self.index(), self.source()))
            .1
    }

    pub fn contract_rows(&self) -> &[FunctionContractRow] {
        self.rows.contracts.get_or_init(|| {
            extract_function_contracts(self.module(), self.index(), self.source(), self.version())
        })
    }

    pub fn control_flow_rows(&self) -> &ControlFlowRows {
        self.rows
            .control_flow
            .get_or_init(|| extract_control_flow(self.module(), self.index(), self.source()))
    }

    pub fn declaration_rows(&self) -> &ModuleDeclarationRows {
        self.rows
            .declarations
            .get_or_init(|| extract_module_declarations(self.module(), self.index(), self.source()))
    }

    pub fn dataclass_rows(&self) -> &[DataclassRow] {
        self.rows
            .dataclasses
            .get_or_init(|| extract_dataclasses(self.module(), self.index(), self.source()))
    }

    pub fn function_rows(&self) -> &(Vec<FunctionMetricRow>, Vec<usize>) {
        self.rows
            .functions
            .get_or_init(|| extract_functions(self.module(), self.index(), self.source()))
    }

    pub fn hygiene_rows(&self) -> &HygieneRows {
        self.rows
            .hygiene
            .get_or_init(|| extract_hygiene(self.module(), self.index(), self.source()))
    }

    pub(crate) fn local_call_edge_rows(&self) -> &[LocalCallEdgeRow] {
        &self
            .rows
            .rule_calls
            .get_or_init(|| extract_rule_calls(self.module(), self.index(), self.source()))
            .1
    }

    pub(crate) fn named_call_rows(&self) -> &[RuleNamedCallRow] {
        &self
            .rows
            .rule_calls
            .get_or_init(|| extract_rule_calls(self.module(), self.index(), self.source()))
            .0
    }

    pub fn outer_state_mutation_rows(&self) -> &[SourceRangeRow] {
        self.rows
            .outer_state_mutations
            .get_or_init(|| extract_outer_state_mutations(self.module(), self.index()))
    }

    pub fn parameter_mutation_rows(&self) -> &[ParameterMutationRow] {
        self.rows
            .parameter_mutations
            .get_or_init(|| extract_parameter_mutations(self.module(), self.index(), self.source()))
    }

    pub(crate) fn parameter_mutation_occurrence_rows(&self) -> &[ParameterMutationOccurrenceRow] {
        self.rows.parameter_mutation_occurrences.get_or_init(|| {
            extract_parameter_mutation_occurrences(self.module(), self.index(), self.source())
        })
    }

    pub(crate) fn reference_rows(&self) -> &ReferenceRows {
        self.rows
            .references
            .get_or_init(|| extract_references(self.module(), self.index(), self.source()))
    }

    pub(crate) fn test_function_rows(&self) -> &[TestFunctionRow] {
        self.rows
            .test_functions
            .get_or_init(|| extract_test_functions(self.module(), self.index(), self.source()))
    }

    pub(crate) fn test_module_rows(&self) -> &TestModuleRows {
        self.rows
            .test_module
            .get_or_init(|| extract_test_module(self.module(), self.index(), self.source()))
    }

    pub(crate) fn extract_rows(&self, family: FactFamily) {
        match family {
            FactFamily::Annotations => {
                let _ = self.annotation_rows();
            }
            FactFamily::AssignmentReferences => {
                let _ = self.assignment_reference_rows();
            }
            FactFamily::ClassDeclarations => {
                let _ = self.class_declaration_rows();
            }
            FactFamily::Comments => {
                let _ = self.comment_rows();
            }
            FactFamily::Comparisons => {
                let _ = self.comparison_rows();
            }
            FactFamily::Contracts => {
                let _ = self.contract_rows();
            }
            FactFamily::ControlFlow => {
                let _ = self.control_flow_rows();
            }
            FactFamily::Dataclasses => {
                let _ = self.dataclass_rows();
            }
            FactFamily::Declarations => {
                let _ = self.declaration_rows();
            }
            FactFamily::Functions => {
                let _ = self.function_rows();
            }
            FactFamily::Hygiene => {
                let _ = self.hygiene_rows();
            }
            FactFamily::LocalCallEdges => {
                let _ = self.local_call_edge_rows();
            }
            FactFamily::NamedCalls => {
                let _ = self.named_call_rows();
            }
            FactFamily::OuterStateMutations => {
                let _ = self.outer_state_mutation_rows();
            }
            FactFamily::ParameterMutations => {
                let _ = self.parameter_mutation_rows();
            }
            FactFamily::ParameterMutationOccurrences => {
                let _ = self.parameter_mutation_occurrence_rows();
            }
            FactFamily::References => {
                let _ = self.reference_rows();
            }
            FactFamily::TestFunctions => {
                let _ = self.test_function_rows();
            }
            FactFamily::TestModule => {
                let _ = self.test_module_rows();
            }
        }
    }
}
