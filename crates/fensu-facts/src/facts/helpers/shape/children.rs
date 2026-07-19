//! Enumerate node children in CPython `iter_child_nodes` field order.

use ruff_python_ast::{Expr, InterpolatedStringElement, InterpolatedStringElements, Pattern, Stmt};
use ruff_text_size::{Ranged, TextRange};

use crate::facts::helpers::shape::expression_children::expression_children;
use crate::facts::helpers::shape::expression_children::{pattern_children, type_param_children};
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::statement_children::{
    if_tail_children, parameters_children, statement_children,
};

pub(crate) fn children<'a>(node: &ShapeNode<'a>, out: &mut Vec<ShapeNode<'a>>) {
    match node {
        ShapeNode::Module(module) => push_statements(&module.body, out),
        ShapeNode::Stmt(statement) => statement_children(statement, out),
        ShapeNode::IfTail(clauses) => if_tail_children(clauses, out),
        ShapeNode::Expr(expression) => expression_children(expression, out),
        ShapeNode::GeneratorInCall(generator, _) => {
            out.push(ShapeNode::Expr(&generator.elt));
            for generator_clause in &generator.generators {
                out.push(ShapeNode::Comprehension(generator_clause));
            }
        }
        ShapeNode::Parameters(parameters) => parameters_children(parameters, out),
        ShapeNode::EmptyParameters => {}
        ShapeNode::Parameter(parameter) => {
            if let Some(annotation) = &parameter.annotation {
                out.push(ShapeNode::Expr(annotation));
            }
        }
        ShapeNode::Keyword(keyword) => out.push(ShapeNode::Expr(&keyword.value)),
        ShapeNode::Comprehension(comprehension) => {
            out.push(ShapeNode::Expr(&comprehension.target));
            out.push(ShapeNode::Expr(&comprehension.iter));
            for condition in &comprehension.ifs {
                out.push(ShapeNode::Expr(condition));
            }
        }
        ShapeNode::ExceptHandler(handler) => {
            if let Some(exception_type) = &handler.type_ {
                out.push(ShapeNode::Expr(exception_type));
            }
            push_statements(&handler.body, out);
        }
        ShapeNode::MatchCase(match_case) => {
            out.push(ShapeNode::Pattern(&match_case.pattern));
            if let Some(guard) = &match_case.guard {
                out.push(ShapeNode::Expr(guard));
            }
            push_statements(&match_case.body, out);
        }
        ShapeNode::WithItem(item) => {
            out.push(ShapeNode::Expr(&item.context_expr));
            if let Some(optional_vars) = &item.optional_vars {
                out.push(ShapeNode::Expr(optional_vars));
            }
        }
        ShapeNode::Alias(_) => {}
        ShapeNode::Pattern(pattern) => pattern_children(pattern, out),
        ShapeNode::TypeParam(type_param) => type_param_children(type_param, out),
        ShapeNode::FormattedValue(element) => {
            out.push(ShapeNode::Expr(&element.expression));
            if let Some(format_spec) = &element.format_spec {
                out.push(ShapeNode::FormatSpec(format_spec));
            }
        }
        ShapeNode::FStringLiteral(_) => {}
        ShapeNode::FormatSpec(format_spec) => {
            let mut literal_span: Option<TextRange> = None;
            push_interpolated_elements(&format_spec.elements, &mut literal_span, out);
            flush_span(&mut literal_span, out);
        }
    }
}

pub(crate) fn push_interpolated_elements<'a>(
    elements: &'a InterpolatedStringElements,
    literal_span: &mut Option<TextRange>,
    out: &mut Vec<ShapeNode<'a>>,
) {
    for element in elements {
        match element {
            InterpolatedStringElement::Literal(literal) => {
                extend_span(literal_span, literal.range());
            }
            InterpolatedStringElement::Interpolation(interpolation) => {
                flush_span(literal_span, out);
                out.push(ShapeNode::FormattedValue(interpolation));
            }
        }
    }
}

pub(crate) fn extend_span(literal_span: &mut Option<TextRange>, range: TextRange) {
    *literal_span = match literal_span {
        Some(existing) => Some(TextRange::new(existing.start(), range.end())),
        None => Some(range),
    };
}

pub(crate) fn flush_span(literal_span: &mut Option<TextRange>, out: &mut Vec<ShapeNode<'_>>) {
    if let Some(range) = literal_span.take() {
        out.push(ShapeNode::FStringLiteral(range));
    }
}

pub(crate) fn push_statements<'a>(statements: &'a [Stmt], out: &mut Vec<ShapeNode<'a>>) {
    for statement in statements {
        out.push(ShapeNode::Stmt(statement));
    }
}

pub(crate) fn push_expressions<'a>(expressions: &'a [Expr], out: &mut Vec<ShapeNode<'a>>) {
    for expression in expressions {
        out.push(ShapeNode::Expr(expression));
    }
}

pub(crate) fn push_comprehensions<'a>(
    comprehensions: &'a [ruff_python_ast::Comprehension],
    out: &mut Vec<ShapeNode<'a>>,
) {
    for comprehension in comprehensions {
        out.push(ShapeNode::Comprehension(comprehension));
    }
}

pub(crate) fn push_patterns<'a>(patterns: &'a [Pattern], out: &mut Vec<ShapeNode<'a>>) {
    for pattern in patterns {
        out.push(ShapeNode::Pattern(pattern));
    }
}

pub(crate) fn push_optional<'a>(expression: Option<&'a Expr>, out: &mut Vec<ShapeNode<'a>>) {
    if let Some(inner) = expression {
        out.push(ShapeNode::Expr(inner));
    }
}
