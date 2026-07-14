//! Extract source comments in token order.

use ruff_python_ast::token::{TokenKind, Tokens};
use ruff_text_size::Ranged;

use crate::facts::helpers::wording::text;
use crate::facts::models::CommentRow;
use crate::positions::models::LineIndex;

/// Return every comment with its tokenize-convention position and trimmed text.
pub fn extract_comments(tokens: &Tokens, source: &str, index: &LineIndex) -> Vec<CommentRow> {
    let mut comments: Vec<CommentRow> = Vec::new();
    for token in tokens.iter() {
        if token.kind() != TokenKind::Comment {
            continue;
        }
        let start = token.range().start().to_usize();
        let end = token.range().end().to_usize();
        let line_start = index.line_start(start);
        let text = source.get(start..end).unwrap_or_default();
        comments.push(CommentRow {
            line: index.locate(start).line,
            column: text::char_column(source, line_start, start),
            text: text::python_trim(text).to_owned(),
        });
    }
    comments
}
