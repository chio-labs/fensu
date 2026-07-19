//! Render annotation expressions the way `ast.unparse` renders them.

use ruff_python_ast::{Expr, Number, Operator};

use crate::constants;

pub(crate) fn unparse_annotation(expression: &Expr) -> Option<String> {
    render(expression, 0)
}

fn render(expression: &Expr, parent_precedence: u8) -> Option<String> {
    match expression {
        Expr::Name(name) => Some(name.id.as_str().to_owned()),
        Expr::Attribute(attribute) => {
            if !is_reference_expression(&attribute.value) {
                return None;
            }
            let value = render(&attribute.value, 0)?;
            Some(format!(
                "{value}{}{}",
                constants::MODULE_SEPARATOR,
                attribute.attr.as_str()
            ))
        }
        Expr::Subscript(subscript) => {
            if !is_reference_expression(&subscript.value) {
                return None;
            }
            let value = render(&subscript.value, 0)?;
            let inner = match &*subscript.slice {
                Expr::Tuple(tuple) if !tuple.elts.is_empty() => elements_view(&tuple.elts)?,
                other => render(other, 0)?,
            };
            Some(format!("{value}[{inner}]"))
        }
        Expr::Tuple(tuple) => {
            if tuple.elts.is_empty() {
                return Some("()".to_owned());
            }
            Some(format!("({})", elements_view(&tuple.elts)?))
        }
        Expr::List(list) => {
            let mut parts: Vec<String> = Vec::with_capacity(list.elts.len());
            for element in &list.elts {
                parts.push(render(element, 0)?);
            }
            Some(format!("[{}]", parts.join(", ")))
        }
        Expr::Starred(starred) => Some(format!("*{}", render(&starred.value, 0)?)),
        Expr::BinOp(binop) => {
            let (precedence, symbol) = operator_precedence(binop.op);
            let left = render(&binop.left, precedence)?;
            let right = render(&binop.right, precedence + 1)?;
            let rendered = format!("{left} {symbol} {right}");
            if precedence < parent_precedence {
                Some(format!("({rendered})"))
            } else {
                Some(rendered)
            }
        }
        Expr::Call(call) => {
            if !is_reference_expression(&call.func) {
                return None;
            }
            let func = render(&call.func, 0)?;
            let mut parts: Vec<String> = Vec::new();
            for argument in &call.arguments.args {
                parts.push(render(argument, 0)?);
            }
            for keyword in &call.arguments.keywords {
                let value = render(&keyword.value, 0)?;
                match &keyword.arg {
                    Some(name) => parts.push(format!("{}={value}", name.as_str())),
                    None => parts.push(format!("**{value}")),
                }
            }
            Some(format!("{func}({})", parts.join(", ")))
        }
        Expr::NoneLiteral(_) => Some("None".to_owned()),
        Expr::EllipsisLiteral(_) => Some("...".to_owned()),
        Expr::BooleanLiteral(literal) => Some(if literal.value {
            "True".to_owned()
        } else {
            "False".to_owned()
        }),
        Expr::StringLiteral(literal) => string_repr(literal.value.to_str()),
        Expr::NumberLiteral(literal) => number_repr(&literal.value),
        _ => None,
    }
}

fn is_reference_expression(expression: &Expr) -> bool {
    matches!(
        expression,
        Expr::Name(_) | Expr::Attribute(_) | Expr::Subscript(_) | Expr::Call(_)
    )
}

fn elements_view(elements: &[Expr]) -> Option<String> {
    let mut parts: Vec<String> = Vec::with_capacity(elements.len());
    for element in elements {
        parts.push(render(element, 0)?);
    }
    if parts.len() == 1 {
        Some(format!("{},", parts[0]))
    } else {
        Some(parts.join(", "))
    }
}

fn operator_precedence(operator: Operator) -> (u8, &'static str) {
    match operator {
        Operator::BitOr => (1, "|"),
        Operator::BitXor => (2, "^"),
        Operator::BitAnd => (3, "&"),
        Operator::LShift => (4, "<<"),
        Operator::RShift => (4, ">>"),
        Operator::Add => (5, "+"),
        Operator::Sub => (5, "-"),
        Operator::Mult => (6, "*"),
        Operator::MatMult => (6, "@"),
        Operator::Div => (6, "/"),
        Operator::Mod => (6, "%"),
        Operator::FloorDiv => (6, "//"),
        Operator::Pow => (7, "**"),
    }
}

fn number_repr(number: &Number) -> Option<String> {
    match number {
        Number::Int(value) => Some(value.to_string()),
        Number::Float(value) => float_repr(*value),
        Number::Complex { real, imag } => {
            if *real != constants::ZERO_FLOAT {
                return None;
            }
            Some(format!("{}j", float_trimmed(*imag)?))
        }
    }
}

fn float_repr(value: f64) -> Option<String> {
    let formatted = float_trimmed(value)?;
    if formatted.contains('.') {
        Some(formatted)
    } else {
        Some(format!("{formatted}.0"))
    }
}

fn float_trimmed(value: f64) -> Option<String> {
    if !value.is_finite() {
        return None;
    }
    let magnitude = value.abs();
    if magnitude != constants::ZERO_FLOAT
        && !(constants::FLOAT_REPR_MIN_MAGNITUDE..constants::FLOAT_REPR_MAX_MAGNITUDE)
            .contains(&magnitude)
    {
        return None;
    }
    Some(format!("{value}"))
}

fn string_repr(text: &str) -> Option<String> {
    let has_single = text.contains('\'');
    let has_double = text.contains('"');
    let quote = if has_single && !has_double { '"' } else { '\'' };
    let mut rendered = String::with_capacity(text.len() + 2);
    rendered.push(quote);
    for character in text.chars() {
        match character {
            '\\' => rendered.push_str("\\\\"),
            '\n' => rendered.push_str("\\n"),
            '\r' => rendered.push_str("\\r"),
            '\t' => rendered.push_str("\\t"),
            _ if character == quote => {
                rendered.push('\\');
                rendered.push(character);
            }
            _ if (character as u32) < constants::CONTROL_CHARACTER_LIMIT
                || (character as u32) == constants::DELETE_CHARACTER =>
            {
                rendered.push_str(&format!("\\x{:02x}", character as u32));
            }
            _ if (character as u32) >= constants::DELETE_CHARACTER => return None,
            _ => rendered.push(character),
        }
    }
    rendered.push(quote);
    Some(rendered)
}
