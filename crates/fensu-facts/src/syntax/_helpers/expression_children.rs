//! Enumerate expression children in CPython `iter_child_nodes` field order.

use ruff_python_ast::{Expr, ExprCall, ExprFString, FStringPart, Pattern, TypeParam};
use ruff_text_size::{Ranged, TextRange};

use crate::syntax::_helpers::children::ChildCollector;
use crate::syntax::types::ShapeNode;

impl<'a> ChildCollector<'a> {
    pub(crate) fn expression_children(&mut self, expression: &'a Expr) {
        match expression {
            Expr::BoolOp(inner) => self.push_expressions(&inner.values),
            Expr::Named(inner) => {
                self.out.push(ShapeNode::Expr(&inner.target));
                self.out.push(ShapeNode::Expr(&inner.value));
            }
            Expr::BinOp(inner) => {
                self.out.push(ShapeNode::Expr(&inner.left));
                self.out.push(ShapeNode::Expr(&inner.right));
            }
            Expr::UnaryOp(inner) => self.out.push(ShapeNode::Expr(&inner.operand)),
            Expr::Lambda(inner) => {
                match inner.parameters.as_deref() {
                    Some(parameters) => self.out.push(ShapeNode::Parameters(parameters)),
                    None => self.out.push(ShapeNode::EmptyParameters),
                }
                self.out.push(ShapeNode::Expr(&inner.body));
            }
            Expr::If(inner) => {
                self.out.push(ShapeNode::Expr(&inner.test));
                self.out.push(ShapeNode::Expr(&inner.body));
                self.out.push(ShapeNode::Expr(&inner.orelse));
            }
            Expr::Dict(inner) => {
                for item in &inner.items {
                    if let Some(key) = &item.key {
                        self.out.push(ShapeNode::Expr(key));
                    }
                }
                for item in &inner.items {
                    self.out.push(ShapeNode::Expr(&item.value));
                }
            }
            Expr::Set(inner) => self.push_expressions(&inner.elts),
            Expr::ListComp(inner) => {
                self.out.push(ShapeNode::Expr(&inner.elt));
                self.push_comprehensions(&inner.generators);
            }
            Expr::SetComp(inner) => {
                self.out.push(ShapeNode::Expr(&inner.elt));
                self.push_comprehensions(&inner.generators);
            }
            Expr::DictComp(inner) => {
                self.push_optional(inner.key.as_deref());
                self.out.push(ShapeNode::Expr(&inner.value));
                self.push_comprehensions(&inner.generators);
            }
            Expr::Generator(inner) => {
                self.out.push(ShapeNode::Expr(&inner.elt));
                self.push_comprehensions(&inner.generators);
            }
            Expr::Await(inner) => self.out.push(ShapeNode::Expr(&inner.value)),
            Expr::Yield(inner) => self.push_optional(inner.value.as_deref()),
            Expr::YieldFrom(inner) => self.out.push(ShapeNode::Expr(&inner.value)),
            Expr::Compare(inner) => {
                self.out.push(ShapeNode::Expr(&inner.left));
                self.push_expressions(&inner.comparators);
            }
            Expr::Call(inner) => self.call_children(inner),
            Expr::FString(inner) => self.fstring_children(inner),
            Expr::Attribute(inner) => self.out.push(ShapeNode::Expr(&inner.value)),
            Expr::Subscript(inner) => {
                self.out.push(ShapeNode::Expr(&inner.value));
                self.out.push(ShapeNode::Expr(&inner.slice));
            }
            Expr::Starred(inner) => self.out.push(ShapeNode::Expr(&inner.value)),
            Expr::List(inner) => self.push_expressions(&inner.elts),
            Expr::Tuple(inner) => self.push_expressions(&inner.elts),
            Expr::Slice(inner) => {
                self.push_optional(inner.lower.as_deref());
                self.push_optional(inner.upper.as_deref());
                self.push_optional(inner.step.as_deref());
            }
            Expr::TString(_)
            | Expr::StringLiteral(_)
            | Expr::BytesLiteral(_)
            | Expr::NumberLiteral(_)
            | Expr::BooleanLiteral(_)
            | Expr::NoneLiteral(_)
            | Expr::EllipsisLiteral(_)
            | Expr::Name(_)
            | Expr::IpyEscapeCommand(_) => {}
        }
    }

    fn call_children(&mut self, call: &'a ExprCall) {
        self.out.push(ShapeNode::Expr(&call.func));
        for argument in &call.arguments.args {
            match argument {
                Expr::Generator(generator) if !generator.parenthesized => {
                    self.out
                        .push(ShapeNode::GeneratorInCall(generator, call.arguments.range));
                }
                _ => self.out.push(ShapeNode::Expr(argument)),
            }
        }
        for keyword in &call.arguments.keywords {
            self.out.push(ShapeNode::Keyword(keyword));
        }
    }

    fn fstring_children(&mut self, fstring: &'a ExprFString) {
        let mut literal_span: Option<TextRange> = None;
        for part in &fstring.value {
            match part {
                FStringPart::Literal(literal) => {
                    literal_span = Self::extend_span(literal_span, literal.range());
                }
                FStringPart::FString(inner) => {
                    literal_span = self.push_interpolated_elements(&inner.elements, literal_span);
                }
            }
        }
        self.flush_span(literal_span);
    }

    pub(crate) fn pattern_children(&mut self, pattern: &'a Pattern) {
        match pattern {
            Pattern::MatchValue(inner) => self.out.push(ShapeNode::Expr(&inner.value)),
            Pattern::MatchSingleton(_) | Pattern::MatchStar(_) => {}
            Pattern::MatchSequence(inner) => self.push_patterns(&inner.patterns),
            Pattern::MatchMapping(inner) => {
                self.push_expressions(&inner.keys);
                self.push_patterns(&inner.patterns);
            }
            Pattern::MatchClass(inner) => {
                self.out.push(ShapeNode::Expr(&inner.cls));
                self.push_patterns(&inner.arguments.patterns);
                for keyword in &inner.arguments.keywords {
                    self.out.push(ShapeNode::Pattern(&keyword.pattern));
                }
            }
            Pattern::MatchAs(inner) => {
                if let Some(inner_pattern) = &inner.pattern {
                    self.out.push(ShapeNode::Pattern(inner_pattern));
                }
            }
            Pattern::MatchOr(inner) => self.push_patterns(&inner.patterns),
        }
    }

    pub(crate) fn type_param_children(&mut self, type_param: &'a TypeParam) {
        match type_param {
            TypeParam::TypeVar(inner) => {
                self.push_optional(inner.bound.as_deref());
                self.push_optional(inner.default.as_deref());
            }
            TypeParam::TypeVarTuple(inner) => self.push_optional(inner.default.as_deref()),
            TypeParam::ParamSpec(inner) => self.push_optional(inner.default.as_deref()),
        }
    }
}
