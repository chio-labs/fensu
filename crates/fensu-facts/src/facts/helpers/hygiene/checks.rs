//! Build syntax-based hygiene rows over the breadth-first arena.

use ruff_python_ast::{Expr, ModModule, Number, Stmt, UnaryOp};

use crate::constants;
use crate::facts::helpers::naming::names::is_docstring_statement;
use crate::facts::helpers::shape::breadth::breadth_first_nodes;
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::HygieneRows;
use crate::positions::models::LineIndex;

pub(crate) fn hygiene_rows(module: &ModModule, index: &LineIndex, source: &str) -> HygieneRows {
    let nodes = breadth_first_nodes(module);
    let mut rows = HygieneRows::default();
    collect_docstrings(module, &nodes, index, source, &mut rows);
    for node in &nodes {
        match node {
            ShapeNode::Stmt(Stmt::Raise(inner)) => {
                let raw = inner
                    .exc
                    .as_deref()
                    .and_then(leftmost_base_name)
                    .is_some_and(|name| constants::RAW_BUILTIN_RAISE_NAMES.contains(&name));
                if raw {
                    rows.raw_builtin_raises.push(start_of(node, index, source));
                }
            }
            ShapeNode::Stmt(Stmt::Assert(_)) => {
                rows.assertions.push(start_of(node, index, source));
            }
            ShapeNode::ExceptHandler(handler) => {
                let bare = handler.name.is_none()
                    && matches!(
                        handler.type_.as_deref(),
                        Some(Expr::Name(name)) if name.id.as_str() == constants::EXCEPTION_CLASS_NAME
                    );
                if bare && body_is_single_swallow(&handler.body) {
                    rows.swallowed_exception_probes
                        .push(start_of(node, index, source));
                }
            }
            _ => {}
        }
    }
    collect_decisions(&nodes, index, source, true, &mut rows);
    collect_decisions(&nodes, index, source, false, &mut rows);
    rows
}

fn collect_docstrings(
    module: &ModModule,
    nodes: &[ShapeNode<'_>],
    index: &LineIndex,
    source: &str,
    rows: &mut HygieneRows,
) {
    let mut owners: Vec<&[Stmt]> = vec![&module.body];
    for want_async in [false, true] {
        for node in nodes {
            if let ShapeNode::Stmt(Stmt::FunctionDef(inner)) = node {
                if inner.is_async == want_async {
                    owners.push(&inner.body);
                }
            }
        }
    }
    for node in nodes {
        if let ShapeNode::Stmt(Stmt::ClassDef(inner)) = node {
            owners.push(&inner.body);
        }
    }
    for body in owners {
        let Some(first) = body.first() else {
            continue;
        };
        if is_multiline_docstring(first, index) {
            rows.multiline_docstrings
                .push(start_of(&ShapeNode::Stmt(first), index, source));
        }
    }
}

fn is_multiline_docstring(statement: &Stmt, index: &LineIndex) -> bool {
    if !is_docstring_statement(statement) {
        return false;
    }
    let Stmt::Expr(inner) = statement else {
        return false;
    };
    let Expr::StringLiteral(literal) = &*inner.value else {
        return false;
    };
    let start_line = index.locate(inner.range.start().to_usize()).line;
    let end_line = index.locate(inner.range.end().to_usize()).line;
    end_line > start_line || literal.value.to_str().contains('\n')
}

fn body_is_single_swallow(body: &[Stmt]) -> bool {
    if body.len() != 1 {
        return false;
    }
    match &body[0] {
        Stmt::Continue(_) => true,
        Stmt::Return(inner) => match inner.value.as_deref() {
            Some(Expr::NoneLiteral(_)) => true,
            Some(Expr::BooleanLiteral(literal)) => !literal.value,
            Some(Expr::Dict(dict)) => dict.items.is_empty(),
            Some(Expr::Tuple(tuple)) => tuple.elts.is_empty(),
            _ => false,
        },
        _ => false,
    }
}

fn collect_decisions(
    nodes: &[ShapeNode<'_>],
    index: &LineIndex,
    source: &str,
    strings: bool,
    rows: &mut HygieneRows,
) {
    for node in nodes {
        let ShapeNode::Expr(Expr::Compare(compare)) = node else {
            continue;
        };
        if strings && is_main_execution_guard(compare) {
            continue;
        }
        let operands = std::iter::once(&*compare.left).chain(compare.comparators.iter());
        for operand in operands {
            for literal in decision_literal_nodes(operand) {
                if strings {
                    if matches!(literal, Expr::StringLiteral(_)) {
                        rows.unnamed_string_decisions.push(start_of(
                            &ShapeNode::Expr(literal),
                            index,
                            source,
                        ));
                    }
                } else if is_magic_numeric_literal(literal) {
                    rows.magic_numeric_comparisons.push(start_of(
                        &ShapeNode::Expr(literal),
                        index,
                        source,
                    ));
                }
            }
        }
    }
}

fn decision_literal_nodes(expression: &Expr) -> Vec<&Expr> {
    match expression {
        Expr::StringLiteral(_)
        | Expr::BytesLiteral(_)
        | Expr::NumberLiteral(_)
        | Expr::BooleanLiteral(_)
        | Expr::NoneLiteral(_)
        | Expr::EllipsisLiteral(_)
        | Expr::UnaryOp(_) => vec![expression],
        Expr::List(inner) => inner.elts.iter().flat_map(decision_literal_nodes).collect(),
        Expr::Set(inner) => inner.elts.iter().flat_map(decision_literal_nodes).collect(),
        Expr::Tuple(inner) => inner.elts.iter().flat_map(decision_literal_nodes).collect(),
        Expr::Call(call) => {
            let named_frozenset = matches!(
                &*call.func,
                Expr::Name(name) if name.id.as_str() == constants::FROZENSET_FUNCTION_NAME
            );
            if named_frozenset
                && call.arguments.args.len() == 1
                && call.arguments.keywords.is_empty()
            {
                decision_literal_nodes(&call.arguments.args[0])
            } else {
                Vec::new()
            }
        }
        _ => Vec::new(),
    }
}

fn is_magic_numeric_literal(expression: &Expr) -> bool {
    match numeric_literal_value(expression) {
        Some(value) => !value_is_canonical(value),
        None => false,
    }
}

enum NumericValue {
    Integer(Option<i64>),
    Float(f64),
    Complex { real: f64, imag: f64 },
}

fn numeric_literal_value(expression: &Expr) -> Option<NumericValue> {
    match expression {
        Expr::NumberLiteral(literal) => Some(number_value(&literal.value, false)),
        Expr::UnaryOp(inner) if matches!(inner.op, UnaryOp::USub) => match &*inner.operand {
            Expr::NumberLiteral(literal) => Some(number_value(&literal.value, true)),
            _ => None,
        },
        _ => None,
    }
}

fn number_value(number: &Number, negated: bool) -> NumericValue {
    let sign = if negated { -1.0 } else { 1.0 };
    match number {
        Number::Int(value) => {
            NumericValue::Integer(
                value
                    .as_i64()
                    .map(|inner| if negated { -inner } else { inner }),
            )
        }
        Number::Float(value) => NumericValue::Float(sign * *value),
        Number::Complex { real, imag } => NumericValue::Complex {
            real: sign * *real,
            imag: sign * *imag,
        },
    }
}

fn value_is_canonical(value: NumericValue) -> bool {
    match value {
        NumericValue::Integer(Some(inner)) => (-1..=1).contains(&inner),
        NumericValue::Integer(None) => false,
        NumericValue::Float(inner) => {
            inner == constants::NEGATIVE_ONE_FLOAT
                || inner == constants::ZERO_FLOAT
                || inner == constants::ONE_FLOAT
        }
        NumericValue::Complex { real, imag } => {
            imag == constants::ZERO_FLOAT
                && (real == constants::NEGATIVE_ONE_FLOAT
                    || real == constants::ZERO_FLOAT
                    || real == constants::ONE_FLOAT)
        }
    }
}

fn is_main_execution_guard(compare: &ruff_python_ast::ExprCompare) -> bool {
    compare.ops.len() == 1
        && matches!(compare.ops[0], ruff_python_ast::CmpOp::Eq)
        && compare.comparators.len() == 1
        && matches!(
            &*compare.left,
            Expr::Name(name) if name.id.as_str() == constants::MODULE_NAME_VARIABLE
        )
        && matches!(
            &compare.comparators[0],
            Expr::StringLiteral(literal) if literal.value.to_str() == constants::MAIN_MODULE_NAME
        )
}

pub(crate) fn leftmost_base_name(expression: &Expr) -> Option<&str> {
    match expression {
        Expr::Name(name) => Some(name.id.as_str()),
        Expr::Attribute(attribute) => leftmost_base_name(&attribute.value),
        Expr::Call(call) => leftmost_base_name(&call.func),
        _ => None,
    }
}
