//! Parse strict dotted reference paths from an expression.

use ruff_python_ast::Expr;

pub(crate) fn strict_reference_parts(expression: &Expr) -> Vec<String> {
    match expression {
        Expr::Name(name) => vec![name.id.as_str().to_owned()],
        Expr::Attribute(attribute) => {
            let mut parent = strict_reference_parts(&attribute.value);
            if parent.is_empty() {
                Vec::new()
            } else {
                parent.push(attribute.attr.as_str().to_owned());
                parent
            }
        }
        Expr::Subscript(subscript) => strict_reference_parts(&subscript.value),
        _ => Vec::new(),
    }
}
