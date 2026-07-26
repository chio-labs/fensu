//! Coordinate declaration-only and complete mapping row extraction.

use ruff_python_ast::{ModModule, Stmt, StmtFunctionDef};
use ruff_text_size::Ranged;

use crate::mapping::_helpers::classes::{class_row, mapping_bases};
use crate::mapping::_helpers::functions::function_row;
use crate::mapping::_helpers::imports::mapping_imports;
use crate::mapping::models::{MappingClassRow, MappingFunctionRow, MappingRows};
use crate::positions::models::LineIndex;
use crate::syntax::main::start_of::start_of;
use crate::syntax::types::ShapeNode;

struct ExtractFunctionParams<'a> {
    function: &'a StmtFunctionDef,
    owning_class: Option<&'a str>,
    index: &'a LineIndex,
    source: &'a str,
    declarations_only: bool,
}

pub(crate) fn build_mapping_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
    declarations_only: bool,
) -> MappingRows {
    let (runtime_imports, annotation_imports) = mapping_imports(module);
    let mut rows = MappingRows {
        runtime_imports,
        annotation_imports,
        ..MappingRows::default()
    };
    for statement in &module.body {
        match statement {
            Stmt::FunctionDef(function) => {
                rows.functions.push(extract_function(ExtractFunctionParams {
                    function,
                    owning_class: None,
                    index,
                    source,
                    declarations_only,
                }))
            }
            Stmt::ClassDef(class) => {
                rows.classes.push(if declarations_only {
                    MappingClassRow {
                        name: class.name.as_str().to_owned(),
                        line: start_of(&ShapeNode::Stmt(statement), index, source).0,
                        bases: mapping_bases(class, source),
                        class_attributes: Vec::new(),
                        instance_attributes: Vec::new(),
                    }
                } else {
                    class_row(class, index, source)
                });
                for child in &class.body {
                    if let Stmt::FunctionDef(function) = child {
                        rows.functions.push(extract_function(ExtractFunctionParams {
                            function,
                            owning_class: Some(class.name.as_str()),
                            index,
                            source,
                            declarations_only,
                        }));
                    }
                }
            }
            _ => {}
        }
    }
    rows
}

fn extract_function(params: ExtractFunctionParams<'_>) -> MappingFunctionRow {
    if !params.declarations_only {
        return function_row(
            params.function,
            params.owning_class,
            params.index,
            params.source,
        );
    }
    MappingFunctionRow {
        name: params.function.name.as_str().to_owned(),
        line: params
            .index
            .locate(params.function.range().start().to_usize())
            .line,
        owning_class: params.owning_class.map(str::to_owned),
        parameters: Vec::new(),
        returns: None,
        statements: Vec::new(),
    }
}
