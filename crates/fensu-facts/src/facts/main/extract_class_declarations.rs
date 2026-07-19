//! Extract class declarations and their direct methods.

use ruff_python_ast::{ModModule, Stmt};

use crate::facts::helpers::naming::names::{class_base_expressions, decorator_name};
use crate::facts::helpers::shape::breadth::breadth_first_with_parents;
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::{ClassDeclarationRow, ClassMethodRow, DefinitionIdentityRow};
use crate::positions::models::LineIndex;

/// Return classes in CPython-compatible breadth-first order.
pub fn extract_class_declarations(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<ClassDeclarationRow> {
    let (nodes, parents) = breadth_first_with_parents(module);
    let mut rows = Vec::new();
    for (position, node) in nodes.iter().enumerate() {
        let ShapeNode::Stmt(Stmt::ClassDef(class)) = node else {
            continue;
        };
        let (line, column) = start_of(node, index, source);
        let identity = DefinitionIdentityRow {
            name: class.name.as_str().to_owned(),
            line,
            column,
        };
        let base_names = class_base_expressions(class)
            .filter_map(crate::facts::helpers::naming::names::subscript_base_name)
            .map(str::to_owned)
            .collect();
        let methods = direct_methods(class, &identity, index, source);
        let decorator_names = class
            .decorator_list
            .iter()
            .map(|decorator| decorator_name(&decorator.expression))
            .filter(|name| !name.is_empty())
            .collect();
        let top_level =
            parents[position].is_some_and(|parent| matches!(nodes[parent], ShapeNode::Module(_)));
        rows.push(ClassDeclarationRow {
            name: identity.name.clone(),
            base_names,
            decorator_names,
            line,
            column,
            top_level,
            methods,
        });
    }
    rows
}

fn direct_methods(
    class: &ruff_python_ast::StmtClassDef,
    identity: &DefinitionIdentityRow,
    index: &LineIndex,
    source: &str,
) -> Vec<ClassMethodRow> {
    let mut methods = Vec::new();
    for statement in &class.body {
        let Stmt::FunctionDef(function) = statement else {
            continue;
        };
        let node = ShapeNode::Stmt(statement);
        let (line, column) = start_of(&node, index, source);
        let decorator_names = function
            .decorator_list
            .iter()
            .map(|decorator| decorator_name(&decorator.expression))
            .filter(|name| !name.is_empty())
            .collect();
        methods.push(ClassMethodRow {
            name: function.name.as_str().to_owned(),
            decorator_names,
            line,
            column,
            owning_class: identity.clone(),
        });
    }
    methods
}
