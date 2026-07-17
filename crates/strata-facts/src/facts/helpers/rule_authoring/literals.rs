//! Literal positional call arguments with Python-compatible values.

use ruff_python_ast::{Expr, Number};
use ruff_text_size::Ranged;

use crate::facts::models::LiteralArgumentRow;
use crate::facts::types::LiteralValueRow;

pub(crate) fn literal_arguments(
    call: &ruff_python_ast::ExprCall,
    source: &str,
) -> Vec<LiteralArgumentRow> {
    call.arguments
        .args
        .iter()
        .enumerate()
        .filter_map(|(position, argument)| literal_argument(position, argument, source))
        .collect()
}

fn literal_argument(
    position: usize,
    expression: &Expr,
    source: &str,
) -> Option<LiteralArgumentRow> {
    let (kind, value) = match expression {
        Expr::StringLiteral(_) => {
            let range = expression.range();
            let literal_source = source.get(range.start().to_usize()..range.end().to_usize())?;
            (
                "string",
                LiteralValueRow::StringSource(literal_source.to_owned()),
            )
        }
        Expr::BytesLiteral(literal) => (
            "bytes",
            LiteralValueRow::Bytes(literal.value.bytes().collect()),
        ),
        Expr::NumberLiteral(literal) => match &literal.value {
            Number::Int(value) => ("integer", LiteralValueRow::Integer(value.to_string())),
            Number::Float(value) => ("float", LiteralValueRow::Float(*value)),
            Number::Complex { real, imag } => (
                "complex",
                LiteralValueRow::Complex {
                    real: *real,
                    imag: *imag,
                },
            ),
        },
        Expr::BooleanLiteral(literal) => ("boolean", LiteralValueRow::Boolean(literal.value)),
        Expr::NoneLiteral(_) => ("none", LiteralValueRow::None),
        Expr::EllipsisLiteral(_) => ("ellipsis", LiteralValueRow::None),
        _ => return None,
    };
    Some(LiteralArgumentRow {
        position,
        kind: kind.to_owned(),
        value,
    })
}
