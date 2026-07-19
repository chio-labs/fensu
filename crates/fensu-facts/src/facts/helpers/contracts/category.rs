//! Categorize return annotations the way the Python contract helper does.

use ruff_python_ast::{Expr, PythonVersion};

use crate::constants;
use crate::facts::helpers::contracts::display::unparse_annotation;
use crate::parsing::main::parse_expression_strict::parse_expression_strict;

pub(crate) fn annotation_category(
    annotation: Option<&Expr>,
    version: PythonVersion,
) -> (&'static str, Option<String>) {
    let Some(expression) = annotation else {
        return (
            constants::MISSING_ANNOTATION_CATEGORY,
            Some(constants::MISSING_ANNOTATION_DISPLAY.to_owned()),
        );
    };
    if let Expr::StringLiteral(literal) = expression {
        let display = literal.value.to_str().to_owned();
        return match parse_expression_strict(literal.value.to_str(), version) {
            Ok(parsed) => (expression_category(&parsed.syntax().body), Some(display)),
            Err(_) => (constants::OTHER_ANNOTATION_CATEGORY, Some(display)),
        };
    }
    (
        expression_category(expression),
        unparse_annotation(expression),
    )
}

fn expression_category(expression: &Expr) -> &'static str {
    if matches!(expression, Expr::NoneLiteral(_)) {
        return constants::NONE_ANNOTATION_CATEGORY;
    }
    let value = match expression {
        Expr::Subscript(subscript) => &*subscript.value,
        other => other,
    };
    let terminal = match value {
        Expr::Name(name) => Some(name.id.as_str()),
        Expr::Attribute(attribute) => Some(attribute.attr.as_str()),
        _ => None,
    };
    let Some(terminal_name) = terminal else {
        return constants::OTHER_ANNOTATION_CATEGORY;
    };
    constants::RETURN_CATEGORY_PAIRS
        .iter()
        .find_map(|(name, category)| (*name == terminal_name).then_some(*category))
        .unwrap_or(constants::OTHER_ANNOTATION_CATEGORY)
}
