//! Parse one UTF-8 Markdown source without imposing an artifact template.

use crate::markdown::helpers::assembly;
use crate::markdown::models::ParsedMarkdown;

/// Return generic Markdown structure and optional Obsidian semantics.
pub fn parse_markdown(source: &str) -> ParsedMarkdown {
    assembly::parse(source)
}
