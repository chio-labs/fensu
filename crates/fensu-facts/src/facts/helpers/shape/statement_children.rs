//! Enumerate statement children in CPython `iter_child_nodes` field order.

use ruff_python_ast::{ElifElseClause, Parameters, Stmt, TypeParams};

use crate::facts::helpers::shape::children::{push_expressions, push_optional, push_statements};
use crate::facts::helpers::shape::nodes::ShapeNode;

pub(crate) fn statement_children<'a>(statement: &'a Stmt, out: &mut Vec<ShapeNode<'a>>) {
    match statement {
        Stmt::FunctionDef(inner) => {
            out.push(ShapeNode::Parameters(&inner.parameters));
            push_statements(&inner.body, out);
            for decorator in &inner.decorator_list {
                out.push(ShapeNode::Expr(&decorator.expression));
            }
            if let Some(returns) = &inner.returns {
                out.push(ShapeNode::Expr(returns));
            }
            push_type_params(inner.type_params.as_deref(), out);
        }
        Stmt::ClassDef(inner) => {
            if let Some(arguments) = &inner.arguments {
                for base in &arguments.args {
                    out.push(ShapeNode::Expr(base));
                }
                for keyword in &arguments.keywords {
                    out.push(ShapeNode::Keyword(keyword));
                }
            }
            push_statements(&inner.body, out);
            for decorator in &inner.decorator_list {
                out.push(ShapeNode::Expr(&decorator.expression));
            }
            push_type_params(inner.type_params.as_deref(), out);
        }
        Stmt::Return(inner) => push_optional(inner.value.as_deref(), out),
        Stmt::Delete(inner) => push_expressions(&inner.targets, out),
        Stmt::TypeAlias(inner) => {
            out.push(ShapeNode::Expr(&inner.name));
            push_type_params(inner.type_params.as_deref(), out);
            out.push(ShapeNode::Expr(&inner.value));
        }
        Stmt::Assign(inner) => {
            push_expressions(&inner.targets, out);
            out.push(ShapeNode::Expr(&inner.value));
        }
        Stmt::AugAssign(inner) => {
            out.push(ShapeNode::Expr(&inner.target));
            out.push(ShapeNode::Expr(&inner.value));
        }
        Stmt::AnnAssign(inner) => {
            out.push(ShapeNode::Expr(&inner.target));
            out.push(ShapeNode::Expr(&inner.annotation));
            push_optional(inner.value.as_deref(), out);
        }
        Stmt::For(inner) => {
            out.push(ShapeNode::Expr(&inner.target));
            out.push(ShapeNode::Expr(&inner.iter));
            push_statements(&inner.body, out);
            push_statements(&inner.orelse, out);
        }
        Stmt::While(inner) => {
            out.push(ShapeNode::Expr(&inner.test));
            push_statements(&inner.body, out);
            push_statements(&inner.orelse, out);
        }
        Stmt::If(inner) => {
            out.push(ShapeNode::Expr(&inner.test));
            push_statements(&inner.body, out);
            push_clause_orelse(&inner.elif_else_clauses, out);
        }
        Stmt::With(inner) => {
            for item in &inner.items {
                out.push(ShapeNode::WithItem(item));
            }
            push_statements(&inner.body, out);
        }
        Stmt::Match(inner) => {
            out.push(ShapeNode::Expr(&inner.subject));
            for match_case in &inner.cases {
                out.push(ShapeNode::MatchCase(match_case));
            }
        }
        Stmt::Raise(inner) => {
            push_optional(inner.exc.as_deref(), out);
            push_optional(inner.cause.as_deref(), out);
        }
        Stmt::Try(inner) => {
            push_statements(&inner.body, out);
            for handler in &inner.handlers {
                let ruff_python_ast::ExceptHandler::ExceptHandler(except_handler) = handler;
                out.push(ShapeNode::ExceptHandler(except_handler));
            }
            push_statements(&inner.orelse, out);
            push_statements(&inner.finalbody, out);
        }
        Stmt::Assert(inner) => {
            out.push(ShapeNode::Expr(&inner.test));
            push_optional(inner.msg.as_deref(), out);
        }
        Stmt::Import(inner) => {
            for alias in &inner.names {
                out.push(ShapeNode::Alias(alias));
            }
        }
        Stmt::ImportFrom(inner) => {
            for alias in &inner.names {
                out.push(ShapeNode::Alias(alias));
            }
        }
        Stmt::Expr(inner) => out.push(ShapeNode::Expr(&inner.value)),
        Stmt::Global(_)
        | Stmt::Nonlocal(_)
        | Stmt::Pass(_)
        | Stmt::Break(_)
        | Stmt::Continue(_)
        | Stmt::IpyEscapeCommand(_) => {}
    }
}

pub(crate) fn if_tail_children<'a>(clauses: &'a [ElifElseClause], out: &mut Vec<ShapeNode<'a>>) {
    let Some((first, rest)) = clauses.split_first() else {
        return;
    };
    if let Some(test) = &first.test {
        out.push(ShapeNode::Expr(test));
    }
    push_statements(&first.body, out);
    push_clause_orelse(rest, out);
}

pub(crate) fn push_clause_orelse<'a>(clauses: &'a [ElifElseClause], out: &mut Vec<ShapeNode<'a>>) {
    let Some(first) = clauses.first() else {
        return;
    };
    if first.test.is_some() {
        out.push(ShapeNode::IfTail(clauses));
    } else {
        push_statements(&first.body, out);
    }
}

pub(crate) fn parameters_children<'a>(parameters: &'a Parameters, out: &mut Vec<ShapeNode<'a>>) {
    for parameter in &parameters.posonlyargs {
        out.push(ShapeNode::Parameter(&parameter.parameter));
    }
    for parameter in &parameters.args {
        out.push(ShapeNode::Parameter(&parameter.parameter));
    }
    if let Some(vararg) = &parameters.vararg {
        out.push(ShapeNode::Parameter(vararg));
    }
    for parameter in &parameters.kwonlyargs {
        out.push(ShapeNode::Parameter(&parameter.parameter));
    }
    for parameter in &parameters.kwonlyargs {
        if let Some(default) = &parameter.default {
            out.push(ShapeNode::Expr(default));
        }
    }
    if let Some(kwarg) = &parameters.kwarg {
        out.push(ShapeNode::Parameter(kwarg));
    }
    for parameter in &parameters.posonlyargs {
        if let Some(default) = &parameter.default {
            out.push(ShapeNode::Expr(default));
        }
    }
    for parameter in &parameters.args {
        if let Some(default) = &parameter.default {
            out.push(ShapeNode::Expr(default));
        }
    }
}

fn push_type_params<'a>(type_params: Option<&'a TypeParams>, out: &mut Vec<ShapeNode<'a>>) {
    if let Some(inner) = type_params {
        for type_param in &inner.type_params {
            out.push(ShapeNode::TypeParam(type_param));
        }
    }
}
