//! Enumerate statement children in CPython `iter_child_nodes` field order.

use ruff_python_ast::{ElifElseClause, Parameters, Stmt, TypeParams};

use crate::syntax::_helpers::children::ChildCollector;
use crate::syntax::types::ShapeNode;

pub(crate) struct ClauseOutput<'out, 'node> {
    pub(crate) out: &'out mut Vec<ShapeNode<'node>>,
}

impl<'node> ClauseOutput<'_, 'node> {
    pub(crate) fn collect(&mut self, clauses: &'node [ElifElseClause]) {
        let current = std::mem::take(self.out);
        *self.out = clause_orelse(clauses, current);
    }
}

impl<'a> ChildCollector<'a> {
    pub(crate) fn statement_children(&mut self, statement: &'a Stmt) {
        match statement {
            Stmt::FunctionDef(inner) => {
                self.out.push(ShapeNode::Parameters(&inner.parameters));
                self.push_statements(&inner.body);
                for decorator in &inner.decorator_list {
                    self.out.push(ShapeNode::Expr(&decorator.expression));
                }
                if let Some(returns) = &inner.returns {
                    self.out.push(ShapeNode::Expr(returns));
                }
                self.push_type_params(inner.type_params.as_deref());
            }
            Stmt::ClassDef(inner) => {
                if let Some(arguments) = &inner.arguments {
                    for base in &arguments.args {
                        self.out.push(ShapeNode::Expr(base));
                    }
                    for keyword in &arguments.keywords {
                        self.out.push(ShapeNode::Keyword(keyword));
                    }
                }
                self.push_statements(&inner.body);
                for decorator in &inner.decorator_list {
                    self.out.push(ShapeNode::Expr(&decorator.expression));
                }
                self.push_type_params(inner.type_params.as_deref());
            }
            Stmt::Return(inner) => self.push_optional(inner.value.as_deref()),
            Stmt::Delete(inner) => self.push_expressions(&inner.targets),
            Stmt::TypeAlias(inner) => {
                self.out.push(ShapeNode::Expr(&inner.name));
                self.push_type_params(inner.type_params.as_deref());
                self.out.push(ShapeNode::Expr(&inner.value));
            }
            Stmt::Assign(inner) => {
                self.push_expressions(&inner.targets);
                self.out.push(ShapeNode::Expr(&inner.value));
            }
            Stmt::AugAssign(inner) => {
                self.out.push(ShapeNode::Expr(&inner.target));
                self.out.push(ShapeNode::Expr(&inner.value));
            }
            Stmt::AnnAssign(inner) => {
                self.out.push(ShapeNode::Expr(&inner.target));
                self.out.push(ShapeNode::Expr(&inner.annotation));
                self.push_optional(inner.value.as_deref());
            }
            Stmt::For(inner) => {
                self.out.push(ShapeNode::Expr(&inner.target));
                self.out.push(ShapeNode::Expr(&inner.iter));
                self.push_statements(&inner.body);
                self.push_statements(&inner.orelse);
            }
            Stmt::While(inner) => {
                self.out.push(ShapeNode::Expr(&inner.test));
                self.push_statements(&inner.body);
                self.push_statements(&inner.orelse);
            }
            Stmt::If(inner) => {
                self.out.push(ShapeNode::Expr(&inner.test));
                self.push_statements(&inner.body);
                self.push_clause_orelse(&inner.elif_else_clauses);
            }
            Stmt::With(inner) => {
                for item in &inner.items {
                    self.out.push(ShapeNode::WithItem(item));
                }
                self.push_statements(&inner.body);
            }
            Stmt::Match(inner) => {
                self.out.push(ShapeNode::Expr(&inner.subject));
                for match_case in &inner.cases {
                    self.out.push(ShapeNode::MatchCase(match_case));
                }
            }
            Stmt::Raise(inner) => {
                self.push_optional(inner.exc.as_deref());
                self.push_optional(inner.cause.as_deref());
            }
            Stmt::Try(inner) => {
                self.push_statements(&inner.body);
                for handler in &inner.handlers {
                    let ruff_python_ast::ExceptHandler::ExceptHandler(except_handler) = handler;
                    self.out.push(ShapeNode::ExceptHandler(except_handler));
                }
                self.push_statements(&inner.orelse);
                self.push_statements(&inner.finalbody);
            }
            Stmt::Assert(inner) => {
                self.out.push(ShapeNode::Expr(&inner.test));
                self.push_optional(inner.msg.as_deref());
            }
            Stmt::Import(inner) => {
                for alias in &inner.names {
                    self.out.push(ShapeNode::Alias(alias));
                }
            }
            Stmt::ImportFrom(inner) => {
                for alias in &inner.names {
                    self.out.push(ShapeNode::Alias(alias));
                }
            }
            Stmt::Expr(inner) => self.out.push(ShapeNode::Expr(&inner.value)),
            Stmt::Global(_)
            | Stmt::Nonlocal(_)
            | Stmt::Pass(_)
            | Stmt::Break(_)
            | Stmt::Continue(_)
            | Stmt::IpyEscapeCommand(_) => {}
        }
    }

    pub(crate) fn if_tail_children(&mut self, clauses: &'a [ElifElseClause]) {
        let Some((first, rest)) = clauses.split_first() else {
            return;
        };
        if let Some(test) = &first.test {
            self.out.push(ShapeNode::Expr(test));
        }
        self.push_statements(&first.body);
        self.push_clause_orelse(rest);
    }

    pub(crate) fn push_clause_orelse(&mut self, clauses: &'a [ElifElseClause]) {
        let Some(first) = clauses.first() else {
            return;
        };
        if first.test.is_some() {
            self.out.push(ShapeNode::IfTail(clauses));
        } else {
            self.push_statements(&first.body);
        }
    }

    pub(crate) fn parameters_children(&mut self, parameters: &'a Parameters) {
        for parameter in &parameters.posonlyargs {
            self.out.push(ShapeNode::Parameter(&parameter.parameter));
        }
        for parameter in &parameters.args {
            self.out.push(ShapeNode::Parameter(&parameter.parameter));
        }
        if let Some(vararg) = &parameters.vararg {
            self.out.push(ShapeNode::Parameter(vararg));
        }
        for parameter in &parameters.kwonlyargs {
            self.out.push(ShapeNode::Parameter(&parameter.parameter));
        }
        for parameter in &parameters.kwonlyargs {
            if let Some(default) = &parameter.default {
                self.out.push(ShapeNode::Expr(default));
            }
        }
        if let Some(kwarg) = &parameters.kwarg {
            self.out.push(ShapeNode::Parameter(kwarg));
        }
        for parameter in &parameters.posonlyargs {
            if let Some(default) = &parameter.default {
                self.out.push(ShapeNode::Expr(default));
            }
        }
        for parameter in &parameters.args {
            if let Some(default) = &parameter.default {
                self.out.push(ShapeNode::Expr(default));
            }
        }
    }

    fn push_type_params(&mut self, type_params: Option<&'a TypeParams>) {
        if let Some(inner) = type_params {
            for type_param in &inner.type_params {
                self.out.push(ShapeNode::TypeParam(type_param));
            }
        }
    }
}

pub(crate) fn clause_orelse<'a>(
    clauses: &'a [ElifElseClause],
    out: Vec<ShapeNode<'a>>,
) -> Vec<ShapeNode<'a>> {
    let mut collector = ChildCollector { out };
    collector.push_clause_orelse(clauses);
    collector.out
}
