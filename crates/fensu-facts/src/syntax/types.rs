//! A CPython-shaped view over ruff syntax nodes.

use ruff_python_ast::{
    Alias, Comprehension, ElifElseClause, ExceptHandlerExceptHandler, Expr, ExprGenerator,
    InterpolatedElement, InterpolatedStringFormatSpec, Keyword, MatchCase, ModModule, Parameter,
    Parameters, Pattern, Stmt, TypeParam, WithItem,
};
use ruff_text_size::TextRange;

/// One node of the CPython-equivalent syntax tree projected from ruff nodes.
#[derive(Clone, Copy)]
pub enum ShapeNode<'a> {
    Module(&'a ModModule),
    Stmt(&'a Stmt),
    IfTail(&'a [ElifElseClause]),
    Expr(&'a Expr),
    GeneratorInCall(&'a ExprGenerator, TextRange),
    Parameters(&'a Parameters),
    EmptyParameters,
    Parameter(&'a Parameter),
    Keyword(&'a Keyword),
    Comprehension(&'a Comprehension),
    ExceptHandler(&'a ExceptHandlerExceptHandler),
    MatchCase(&'a MatchCase),
    WithItem(&'a WithItem),
    Alias(&'a Alias),
    Pattern(&'a Pattern),
    TypeParam(&'a TypeParam),
    FormattedValue(&'a InterpolatedElement),
    FStringLiteral(TextRange),
    FormatSpec(&'a InterpolatedStringFormatSpec),
}
