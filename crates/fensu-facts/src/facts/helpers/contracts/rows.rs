//! Assemble descriptive function-contract rows.

use ruff_python_ast::{ModModule, PythonVersion, Stmt};

use crate::facts::helpers::contracts::category::annotation_category;
use crate::facts::helpers::contracts::returns::owned_return_shape;
use crate::facts::helpers::shape::breadth::breadth_first_nodes;
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::FunctionContractRow;
use crate::positions::models::LineIndex;

pub(crate) fn function_contract_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
    version: PythonVersion,
) -> Vec<FunctionContractRow> {
    let mut rows: Vec<FunctionContractRow> = Vec::new();
    for statement in ordered_functions(module, index, source) {
        let Stmt::FunctionDef(function) = statement else {
            continue;
        };
        let (line, column) = start_of(&ShapeNode::Stmt(statement), index, source);
        let (meaningful_return, contains_yield) = owned_return_shape(&function.body);
        let (category, annotation) = annotation_category(function.returns.as_deref(), version);
        rows.push(FunctionContractRow {
            function_name: function.name.as_str().to_owned(),
            line,
            column,
            category: category.to_owned(),
            annotation,
            contains_yield,
            meaningful_return: meaningful_return.map(|range| {
                let location = index.locate(range.start().to_usize());
                (location.line, location.column)
            }),
        });
    }
    rows
}

pub(crate) fn ordered_functions<'a>(
    module: &'a ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<&'a Stmt> {
    let nodes = breadth_first_nodes(module);
    let mut ordered: Vec<&'a Stmt> = Vec::new();
    for want_async in [false, true] {
        for node in &nodes {
            let ShapeNode::Stmt(statement) = node else {
                continue;
            };
            let Stmt::FunctionDef(function) = statement else {
                continue;
            };
            if function.is_async == want_async {
                ordered.push(statement);
            }
        }
    }
    ordered.sort_by_key(|statement| start_of(&ShapeNode::Stmt(statement), index, source));
    ordered
}
