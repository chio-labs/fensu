//! Extract missing-annotation facts from one shared traversal.

use ruff_python_ast::ModModule;

use crate::facts::helpers::annotations::visitor::{
    class_attribute_rows, module_variable_rows, AnnotationVisitor,
};
use crate::facts::models::AnnotationRows;
use crate::positions::models::LineIndex;

/// Return missing parameter, return, local, and variable annotation rows.
pub fn extract_annotations(module: &ModModule, index: &LineIndex, source: &str) -> AnnotationRows {
    let mut rows = AnnotationVisitor::collect(module, index, source);
    rows.module_variables = module_variable_rows(module, index, source);
    rows.class_attributes = class_attribute_rows(module, index, source);
    rows
}
