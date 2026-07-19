//! Fenced and indented code block extraction.

use std::ops::Range;

use pulldown_cmark::{CodeBlockKind as PulldownCodeBlockKind, Event, Parser, Tag, TagEnd};

use crate::markdown::helpers::line_index::LineIndex;
use crate::markdown::helpers::text;
use crate::markdown::models::MarkdownCodeBlock;
use crate::markdown::types::CodeBlockKind;

#[derive(Debug)]
struct ActiveCodeBlock {
    kind: CodeBlockKind,
    info: Option<String>,
    content: String,
    range: Range<usize>,
}

pub(crate) fn extract(source: &str, index: &LineIndex) -> Vec<MarkdownCodeBlock> {
    let parser = Parser::new_ext(source, text::parser_options()).into_offset_iter();
    let mut blocks = Vec::new();
    let mut active: Option<ActiveCodeBlock> = None;
    for (event, range) in parser {
        match event {
            Event::Start(Tag::CodeBlock(kind)) => {
                let (block_kind, info) = code_kind(kind);
                active = Some(ActiveCodeBlock {
                    kind: block_kind,
                    info,
                    content: String::new(),
                    range,
                });
            }
            Event::Text(value) => {
                if let Some(block) = active.as_mut() {
                    block.content.push_str(&value);
                }
            }
            Event::End(TagEnd::CodeBlock) => {
                if let Some(block) = active.take() {
                    blocks.push(build_block(source, index, block, blocks.len()));
                }
            }
            _ => {}
        }
    }
    blocks
}

fn build_block(
    source: &str,
    index: &LineIndex,
    block: ActiveCodeBlock,
    prior_count: usize,
) -> MarkdownCodeBlock {
    let language = block
        .info
        .as_deref()
        .and_then(|info| info.split_whitespace().next())
        .filter(|language| !language.is_empty())
        .map(str::to_owned);
    MarkdownCodeBlock {
        ordinal: prior_count + 1,
        kind: block.kind,
        info: block.info,
        language,
        raw_content: block.content,
        raw_markdown: source
            .get(block.range.clone())
            .unwrap_or_default()
            .to_owned(),
        source_line: index.line_number(block.range.start),
        source_range: index.source_range(block.range),
    }
}

fn code_kind(kind: PulldownCodeBlockKind<'_>) -> (CodeBlockKind, Option<String>) {
    match kind {
        PulldownCodeBlockKind::Indented => (CodeBlockKind::Indented, None),
        PulldownCodeBlockKind::Fenced(info) => {
            let trimmed = info.trim();
            (
                CodeBlockKind::Fenced,
                (!trimmed.is_empty()).then(|| trimmed.to_owned()),
            )
        }
    }
}
