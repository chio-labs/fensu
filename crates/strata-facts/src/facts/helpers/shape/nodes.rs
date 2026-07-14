//! A CPython-shaped view over ruff syntax nodes.

use ruff_python_ast::{
    Alias, Comprehension, ElifElseClause, ExceptHandlerExceptHandler, Expr, ExprGenerator,
    InterpolatedElement, InterpolatedStringFormatSpec, Keyword, MatchCase, ModModule, Parameter,
    Parameters, Pattern, Stmt, TypeParam, WithItem,
};
use ruff_text_size::TextRange;

/// One node of the CPython-equivalent syntax tree projected from ruff nodes.
#[derive(Clone, Copy)]
pub(crate) enum ShapeNode<'a> {
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

pub(crate) fn kind_name(node: &ShapeNode<'_>) -> &'static str {
    match node {
        ShapeNode::Module(_) => "Module",
        ShapeNode::Stmt(statement) => statement_kind_name(statement),
        ShapeNode::IfTail(_) => "If",
        ShapeNode::Expr(expression) => expression_kind_name(expression),
        ShapeNode::GeneratorInCall(_, _) => "GeneratorExp",
        ShapeNode::Parameters(_) | ShapeNode::EmptyParameters => "arguments",
        ShapeNode::Parameter(_) => "arg",
        ShapeNode::Keyword(_) => "keyword",
        ShapeNode::Comprehension(_) => "comprehension",
        ShapeNode::ExceptHandler(_) => "ExceptHandler",
        ShapeNode::MatchCase(_) => "match_case",
        ShapeNode::WithItem(_) => "withitem",
        ShapeNode::Alias(_) => "alias",
        ShapeNode::Pattern(pattern) => pattern_kind_name(pattern),
        ShapeNode::TypeParam(type_param) => type_param_kind_name(type_param),
        ShapeNode::FormattedValue(_) => "FormattedValue",
        ShapeNode::FStringLiteral(_) => "Constant",
        ShapeNode::FormatSpec(_) => "JoinedStr",
    }
}

fn statement_kind_name(statement: &Stmt) -> &'static str {
    match statement {
        Stmt::FunctionDef(inner) if inner.is_async => "AsyncFunctionDef",
        Stmt::FunctionDef(_) => "FunctionDef",
        Stmt::ClassDef(_) => "ClassDef",
        Stmt::Return(_) => "Return",
        Stmt::Delete(_) => "Delete",
        Stmt::TypeAlias(_) => "TypeAlias",
        Stmt::Assign(_) => "Assign",
        Stmt::AugAssign(_) => "AugAssign",
        Stmt::AnnAssign(_) => "AnnAssign",
        Stmt::For(inner) if inner.is_async => "AsyncFor",
        Stmt::For(_) => "For",
        Stmt::While(_) => "While",
        Stmt::If(_) => "If",
        Stmt::With(inner) if inner.is_async => "AsyncWith",
        Stmt::With(_) => "With",
        Stmt::Match(_) => "Match",
        Stmt::Raise(_) => "Raise",
        Stmt::Try(inner) if inner.is_star => "TryStar",
        Stmt::Try(_) => "Try",
        Stmt::Assert(_) => "Assert",
        Stmt::Import(_) => "Import",
        Stmt::ImportFrom(_) => "ImportFrom",
        Stmt::Global(_) => "Global",
        Stmt::Nonlocal(_) => "Nonlocal",
        Stmt::Expr(_) => "Expr",
        Stmt::Pass(_) => "Pass",
        Stmt::Break(_) => "Break",
        Stmt::Continue(_) => "Continue",
        Stmt::IpyEscapeCommand(_) => "IpyEscapeCommand",
    }
}

fn expression_kind_name(expression: &Expr) -> &'static str {
    match expression {
        Expr::BoolOp(_) => "BoolOp",
        Expr::Named(_) => "NamedExpr",
        Expr::BinOp(_) => "BinOp",
        Expr::UnaryOp(_) => "UnaryOp",
        Expr::Lambda(_) => "Lambda",
        Expr::If(_) => "IfExp",
        Expr::Dict(_) => "Dict",
        Expr::Set(_) => "Set",
        Expr::ListComp(_) => "ListComp",
        Expr::SetComp(_) => "SetComp",
        Expr::DictComp(_) => "DictComp",
        Expr::Generator(_) => "GeneratorExp",
        Expr::Await(_) => "Await",
        Expr::Yield(_) => "Yield",
        Expr::YieldFrom(_) => "YieldFrom",
        Expr::Compare(_) => "Compare",
        Expr::Call(_) => "Call",
        Expr::FString(_) => "JoinedStr",
        Expr::TString(_) => "TemplateStr",
        Expr::StringLiteral(_)
        | Expr::BytesLiteral(_)
        | Expr::NumberLiteral(_)
        | Expr::BooleanLiteral(_)
        | Expr::NoneLiteral(_)
        | Expr::EllipsisLiteral(_) => "Constant",
        Expr::Attribute(_) => "Attribute",
        Expr::Subscript(_) => "Subscript",
        Expr::Starred(_) => "Starred",
        Expr::Name(_) => "Name",
        Expr::List(_) => "List",
        Expr::Tuple(_) => "Tuple",
        Expr::Slice(_) => "Slice",
        Expr::IpyEscapeCommand(_) => "IpyEscapeCommand",
    }
}

fn pattern_kind_name(pattern: &Pattern) -> &'static str {
    match pattern {
        Pattern::MatchValue(_) => "MatchValue",
        Pattern::MatchSingleton(_) => "MatchSingleton",
        Pattern::MatchSequence(_) => "MatchSequence",
        Pattern::MatchMapping(_) => "MatchMapping",
        Pattern::MatchClass(_) => "MatchClass",
        Pattern::MatchStar(_) => "MatchStar",
        Pattern::MatchAs(_) => "MatchAs",
        Pattern::MatchOr(_) => "MatchOr",
    }
}

fn type_param_kind_name(type_param: &TypeParam) -> &'static str {
    match type_param {
        TypeParam::TypeVar(_) => "TypeVar",
        TypeParam::TypeVarTuple(_) => "TypeVarTuple",
        TypeParam::ParamSpec(_) => "ParamSpec",
    }
}
