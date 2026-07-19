//! Coordinate declaration-only and complete mapping row extraction.

use ruff_python_ast::{ModModule, Stmt, StmtFunctionDef};
use ruff_text_size::Ranged;

use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::mapping::helpers::classes::class_row;
use crate::facts::mapping::helpers::expressions::expression_row;
use crate::facts::mapping::helpers::functions::function_row;
use crate::facts::mapping::helpers::imports::mapping_imports;
use crate::facts::mapping::models::{MappingClassRow, MappingFunctionRow, MappingRows};
use crate::positions::models::LineIndex;

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
            Stmt::FunctionDef(function) => rows.functions.push(extract_function(
                function,
                None,
                index,
                source,
                declarations_only,
            )),
            Stmt::ClassDef(class) => {
                rows.classes.push(if declarations_only {
                    MappingClassRow {
                        name: class.name.as_str().to_owned(),
                        line: start_of(&ShapeNode::Stmt(statement), index, source).0,
                        bases: class
                            .arguments
                            .as_ref()
                            .map(|arguments| {
                                arguments
                                    .args
                                    .iter()
                                    .map(|expression| expression_row(expression, source))
                                    .collect()
                            })
                            .unwrap_or_default(),
                        class_attributes: Vec::new(),
                        instance_attributes: Vec::new(),
                    }
                } else {
                    class_row(class, index, source)
                });
                for child in &class.body {
                    if let Stmt::FunctionDef(function) = child {
                        rows.functions.push(extract_function(
                            function,
                            Some(class.name.as_str()),
                            index,
                            source,
                            declarations_only,
                        ));
                    }
                }
            }
            _ => {}
        }
    }
    rows
}

fn extract_function(
    function: &StmtFunctionDef,
    owning_class: Option<&str>,
    index: &LineIndex,
    source: &str,
    declarations_only: bool,
) -> MappingFunctionRow {
    if !declarations_only {
        return function_row(function, owning_class, index, source);
    }
    MappingFunctionRow {
        name: function.name.as_str().to_owned(),
        line: index.locate(function.range().start().to_usize()).line,
        owning_class: owning_class.map(str::to_owned),
        parameters: Vec::new(),
        returns: None,
        statements: Vec::new(),
    }
}
