//! Enumerate node children in CPython `iter_child_nodes` field order.

use ruff_python_ast::{Expr, InterpolatedStringElement, InterpolatedStringElements, Pattern, Stmt};
use ruff_text_size::{Ranged, TextRange};

use crate::syntax::types::ShapeNode;

pub(crate) struct ChildCollector<'a> {
    pub(crate) out: Vec<ShapeNode<'a>>,
}

pub(crate) struct ChildOutput<'out, 'node> {
    pub(crate) out: &'out mut Vec<ShapeNode<'node>>,
}

impl<'node> ChildOutput<'_, 'node> {
    pub(crate) fn collect(&mut self, node: &ShapeNode<'node>) {
        let current = std::mem::take(self.out);
        *self.out = children(node, current);
    }
}

pub(crate) fn children<'a>(node: &ShapeNode<'a>, out: Vec<ShapeNode<'a>>) -> Vec<ShapeNode<'a>> {
    let mut collector = ChildCollector { out };
    collector.collect(node);
    collector.out
}

impl<'a> ChildCollector<'a> {
    pub(crate) fn collect(&mut self, node: &ShapeNode<'a>) {
        match node {
            ShapeNode::Module(module) => self.push_statements(&module.body),
            ShapeNode::Stmt(statement) => self.statement_children(statement),
            ShapeNode::IfTail(clauses) => self.if_tail_children(clauses),
            ShapeNode::Expr(expression) => self.expression_children(expression),
            ShapeNode::GeneratorInCall(generator, _) => {
                self.out.push(ShapeNode::Expr(&generator.elt));
                for generator_clause in &generator.generators {
                    self.out.push(ShapeNode::Comprehension(generator_clause));
                }
            }
            ShapeNode::Parameters(parameters) => self.parameters_children(parameters),
            ShapeNode::EmptyParameters => {}
            ShapeNode::Parameter(parameter) => {
                if let Some(annotation) = &parameter.annotation {
                    self.out.push(ShapeNode::Expr(annotation));
                }
            }
            ShapeNode::Keyword(keyword) => self.out.push(ShapeNode::Expr(&keyword.value)),
            ShapeNode::Comprehension(comprehension) => {
                self.out.push(ShapeNode::Expr(&comprehension.target));
                self.out.push(ShapeNode::Expr(&comprehension.iter));
                for condition in &comprehension.ifs {
                    self.out.push(ShapeNode::Expr(condition));
                }
            }
            ShapeNode::ExceptHandler(handler) => {
                if let Some(exception_type) = &handler.type_ {
                    self.out.push(ShapeNode::Expr(exception_type));
                }
                self.push_statements(&handler.body);
            }
            ShapeNode::MatchCase(match_case) => {
                self.out.push(ShapeNode::Pattern(&match_case.pattern));
                if let Some(guard) = &match_case.guard {
                    self.out.push(ShapeNode::Expr(guard));
                }
                self.push_statements(&match_case.body);
            }
            ShapeNode::WithItem(item) => {
                self.out.push(ShapeNode::Expr(&item.context_expr));
                if let Some(optional_vars) = &item.optional_vars {
                    self.out.push(ShapeNode::Expr(optional_vars));
                }
            }
            ShapeNode::Alias(_) => {}
            ShapeNode::Pattern(pattern) => self.pattern_children(pattern),
            ShapeNode::TypeParam(type_param) => self.type_param_children(type_param),
            ShapeNode::FormattedValue(element) => {
                self.out.push(ShapeNode::Expr(&element.expression));
                if let Some(format_spec) = &element.format_spec {
                    self.out.push(ShapeNode::FormatSpec(format_spec));
                }
            }
            ShapeNode::FStringLiteral(_) => {}
            ShapeNode::FormatSpec(format_spec) => {
                let mut literal_span: Option<TextRange> = None;
                literal_span = self.push_interpolated_elements(&format_spec.elements, literal_span);
                self.flush_span(literal_span);
            }
        }
    }

    pub(crate) fn push_interpolated_elements(
        &mut self,
        elements: &'a InterpolatedStringElements,
        mut literal_span: Option<TextRange>,
    ) -> Option<TextRange> {
        for element in elements {
            match element {
                InterpolatedStringElement::Literal(literal) => {
                    literal_span = Self::extend_span(literal_span, literal.range());
                }
                InterpolatedStringElement::Interpolation(interpolation) => {
                    self.flush_span(literal_span);
                    literal_span = None;
                    self.out.push(ShapeNode::FormattedValue(interpolation));
                }
            }
        }
        literal_span
    }

    pub(crate) fn extend_span(
        literal_span: Option<TextRange>,
        range: TextRange,
    ) -> Option<TextRange> {
        match literal_span {
            Some(existing) => Some(TextRange::new(existing.start(), range.end())),
            None => Some(range),
        }
    }

    pub(crate) fn flush_span(&mut self, literal_span: Option<TextRange>) {
        if let Some(range) = literal_span {
            self.out.push(ShapeNode::FStringLiteral(range));
        }
    }

    pub(crate) fn push_statements(&mut self, statements: &'a [Stmt]) {
        for statement in statements {
            self.out.push(ShapeNode::Stmt(statement));
        }
    }

    pub(crate) fn push_expressions(&mut self, expressions: &'a [Expr]) {
        for expression in expressions {
            self.out.push(ShapeNode::Expr(expression));
        }
    }

    pub(crate) fn push_comprehensions(
        &mut self,
        comprehensions: &'a [ruff_python_ast::Comprehension],
    ) {
        for comprehension in comprehensions {
            self.out.push(ShapeNode::Comprehension(comprehension));
        }
    }

    pub(crate) fn push_patterns(&mut self, patterns: &'a [Pattern]) {
        for pattern in patterns {
            self.out.push(ShapeNode::Pattern(pattern));
        }
    }

    pub(crate) fn push_optional(&mut self, expression: Option<&'a Expr>) {
        if let Some(inner) = expression {
            self.out.push(ShapeNode::Expr(inner));
        }
    }
}
