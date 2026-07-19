//! Enumerate expression children in CPython `iter_child_nodes` field order.

use ruff_python_ast::{Expr, ExprCall, ExprFString, FStringPart, Pattern, TypeParam};
use ruff_text_size::{Ranged, TextRange};

use crate::facts::helpers::shape::children::{
    extend_span, flush_span, push_comprehensions, push_expressions, push_interpolated_elements,
    push_optional, push_patterns,
};
use crate::facts::helpers::shape::nodes::ShapeNode;

pub(crate) fn expression_children<'a>(expression: &'a Expr, out: &mut Vec<ShapeNode<'a>>) {
    match expression {
        Expr::BoolOp(inner) => push_expressions(&inner.values, out),
        Expr::Named(inner) => {
            out.push(ShapeNode::Expr(&inner.target));
            out.push(ShapeNode::Expr(&inner.value));
        }
        Expr::BinOp(inner) => {
            out.push(ShapeNode::Expr(&inner.left));
            out.push(ShapeNode::Expr(&inner.right));
        }
        Expr::UnaryOp(inner) => out.push(ShapeNode::Expr(&inner.operand)),
        Expr::Lambda(inner) => {
            match inner.parameters.as_deref() {
                Some(parameters) => out.push(ShapeNode::Parameters(parameters)),
                None => out.push(ShapeNode::EmptyParameters),
            }
            out.push(ShapeNode::Expr(&inner.body));
        }
        Expr::If(inner) => {
            out.push(ShapeNode::Expr(&inner.test));
            out.push(ShapeNode::Expr(&inner.body));
            out.push(ShapeNode::Expr(&inner.orelse));
        }
        Expr::Dict(inner) => {
            for item in &inner.items {
                if let Some(key) = &item.key {
                    out.push(ShapeNode::Expr(key));
                }
            }
            for item in &inner.items {
                out.push(ShapeNode::Expr(&item.value));
            }
        }
        Expr::Set(inner) => push_expressions(&inner.elts, out),
        Expr::ListComp(inner) => {
            out.push(ShapeNode::Expr(&inner.elt));
            push_comprehensions(&inner.generators, out);
        }
        Expr::SetComp(inner) => {
            out.push(ShapeNode::Expr(&inner.elt));
            push_comprehensions(&inner.generators, out);
        }
        Expr::DictComp(inner) => {
            push_optional(inner.key.as_deref(), out);
            out.push(ShapeNode::Expr(&inner.value));
            push_comprehensions(&inner.generators, out);
        }
        Expr::Generator(inner) => {
            out.push(ShapeNode::Expr(&inner.elt));
            push_comprehensions(&inner.generators, out);
        }
        Expr::Await(inner) => out.push(ShapeNode::Expr(&inner.value)),
        Expr::Yield(inner) => push_optional(inner.value.as_deref(), out),
        Expr::YieldFrom(inner) => out.push(ShapeNode::Expr(&inner.value)),
        Expr::Compare(inner) => {
            out.push(ShapeNode::Expr(&inner.left));
            push_expressions(&inner.comparators, out);
        }
        Expr::Call(inner) => call_children(inner, out),
        Expr::FString(inner) => fstring_children(inner, out),
        Expr::Attribute(inner) => out.push(ShapeNode::Expr(&inner.value)),
        Expr::Subscript(inner) => {
            out.push(ShapeNode::Expr(&inner.value));
            out.push(ShapeNode::Expr(&inner.slice));
        }
        Expr::Starred(inner) => out.push(ShapeNode::Expr(&inner.value)),
        Expr::List(inner) => push_expressions(&inner.elts, out),
        Expr::Tuple(inner) => push_expressions(&inner.elts, out),
        Expr::Slice(inner) => {
            push_optional(inner.lower.as_deref(), out);
            push_optional(inner.upper.as_deref(), out);
            push_optional(inner.step.as_deref(), out);
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

fn call_children<'a>(call: &'a ExprCall, out: &mut Vec<ShapeNode<'a>>) {
    out.push(ShapeNode::Expr(&call.func));
    for argument in &call.arguments.args {
        match argument {
            Expr::Generator(generator) if !generator.parenthesized => {
                out.push(ShapeNode::GeneratorInCall(generator, call.arguments.range));
            }
            _ => out.push(ShapeNode::Expr(argument)),
        }
    }
    for keyword in &call.arguments.keywords {
        out.push(ShapeNode::Keyword(keyword));
    }
}

fn fstring_children<'a>(fstring: &'a ExprFString, out: &mut Vec<ShapeNode<'a>>) {
    let mut literal_span: Option<TextRange> = None;
    for part in &fstring.value {
        match part {
            FStringPart::Literal(literal) => extend_span(&mut literal_span, literal.range()),
            FStringPart::FString(inner) => {
                push_interpolated_elements(&inner.elements, &mut literal_span, out);
            }
        }
    }
    flush_span(&mut literal_span, out);
}

pub(crate) fn pattern_children<'a>(pattern: &'a Pattern, out: &mut Vec<ShapeNode<'a>>) {
    match pattern {
        Pattern::MatchValue(inner) => out.push(ShapeNode::Expr(&inner.value)),
        Pattern::MatchSingleton(_) | Pattern::MatchStar(_) => {}
        Pattern::MatchSequence(inner) => push_patterns(&inner.patterns, out),
        Pattern::MatchMapping(inner) => {
            push_expressions(&inner.keys, out);
            push_patterns(&inner.patterns, out);
        }
        Pattern::MatchClass(inner) => {
            out.push(ShapeNode::Expr(&inner.cls));
            push_patterns(&inner.arguments.patterns, out);
            for keyword in &inner.arguments.keywords {
                out.push(ShapeNode::Pattern(&keyword.pattern));
            }
        }
        Pattern::MatchAs(inner) => {
            if let Some(inner_pattern) = &inner.pattern {
                out.push(ShapeNode::Pattern(inner_pattern));
            }
        }
        Pattern::MatchOr(inner) => push_patterns(&inner.patterns, out),
    }
}

pub(crate) fn type_param_children<'a>(type_param: &'a TypeParam, out: &mut Vec<ShapeNode<'a>>) {
    match type_param {
        TypeParam::TypeVar(inner) => {
            push_optional(inner.bound.as_deref(), out);
            push_optional(inner.default.as_deref(), out);
        }
        TypeParam::TypeVarTuple(inner) => push_optional(inner.default.as_deref(), out),
        TypeParam::ParamSpec(inner) => push_optional(inner.default.as_deref(), out),
    }
}
