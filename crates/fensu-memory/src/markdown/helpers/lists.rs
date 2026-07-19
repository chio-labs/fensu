//! Ordered, unordered, nested, checkbox, and relationship list extraction.

use std::ops::Range;

use pulldown_cmark::{Event, Parser, Tag, TagEnd};

use crate::markdown::constants::RELATIONSHIP_KINDS;
use crate::markdown::helpers::line_index::LineIndex;
use crate::markdown::helpers::text;
use crate::markdown::models::{MarkdownCheckbox, MarkdownListItem};
use crate::markdown::types::{CheckboxState, ListKind, RelationshipKind};

#[derive(Debug)]
struct ListContext {
    kind: ListKind,
    next_number: Option<u64>,
}

#[derive(Debug)]
struct ActiveItem {
    ordinal: usize,
    kind: ListKind,
    ordered_number: Option<u64>,
    nesting_depth: usize,
    parent_ordinal: Option<usize>,
    plain_text: String,
    range: Range<usize>,
}

pub(crate) fn extract(source: &str, index: &LineIndex) -> Vec<MarkdownListItem> {
    let parser = Parser::new_ext(source, text::parser_options()).into_offset_iter();
    let mut list_stack: Vec<ListContext> = Vec::new();
    let mut item_stack: Vec<ActiveItem> = Vec::new();
    let mut items = Vec::new();
    let mut next_ordinal = 1;
    for (event, range) in parser {
        match event {
            Event::Start(Tag::List(start)) => list_stack.push(ListContext {
                kind: if start.is_some() {
                    ListKind::Ordered
                } else {
                    ListKind::Unordered
                },
                next_number: start,
            }),
            Event::End(TagEnd::List(_)) => {
                let _ = list_stack.pop();
            }
            Event::Start(Tag::Item) => {
                if let Some(context) = list_stack.last_mut() {
                    let ordered_number = context.next_number;
                    context.next_number =
                        context.next_number.map(|number| number.saturating_add(1));
                    item_stack.push(ActiveItem {
                        ordinal: next_ordinal,
                        kind: context.kind,
                        ordered_number,
                        nesting_depth: list_stack.len().saturating_sub(1),
                        parent_ordinal: item_stack.last().map(|item| item.ordinal),
                        plain_text: String::new(),
                        range,
                    });
                    next_ordinal += 1;
                }
            }
            Event::Text(value)
            | Event::Code(value)
            | Event::InlineMath(value)
            | Event::DisplayMath(value)
            | Event::FootnoteReference(value) => {
                if let Some(item) = item_stack.last_mut() {
                    item.plain_text.push_str(&value);
                }
            }
            Event::SoftBreak | Event::HardBreak => {
                if let Some(item) = item_stack.last_mut() {
                    item.plain_text.push('\n');
                }
            }
            Event::End(TagEnd::Item) => {
                if let Some(item) = item_stack.pop() {
                    items.push(build_item(source, index, item));
                }
            }
            _ => {}
        }
    }
    items.sort_by_key(|item| item.ordinal);
    items
}

fn build_item(source: &str, index: &LineIndex, item: ActiveItem) -> MarkdownListItem {
    let raw = source
        .get(item.range.clone())
        .unwrap_or_default()
        .to_owned();
    let checkbox = checkbox(&raw);
    let plain = strip_checkbox(item.plain_text.trim(), checkbox.as_ref()).to_owned();
    let leading_key = leading_key(&plain);
    let relationship_kind = leading_key.as_deref().and_then(relationship_kind);
    MarkdownListItem {
        ordinal: item.ordinal,
        kind: item.kind,
        ordered_number: item.ordered_number,
        nesting_depth: item.nesting_depth,
        parent_ordinal: item.parent_ordinal,
        raw_markdown: raw.trim_end().to_owned(),
        plain_text: plain,
        source_line: index.line_number(item.range.start),
        source_range: index.source_range(item.range),
        section_ordinal: None,
        checkbox,
        leading_key,
        relationship_kind,
    }
}

fn checkbox(raw_item: &str) -> Option<MarkdownCheckbox> {
    let body = list_body(raw_item)?;
    let rest = body.strip_prefix('[')?;
    let mut characters = rest.chars();
    let marker = characters.next()?;
    if characters.next()? != ']' {
        return None;
    }
    if characters
        .next()
        .is_some_and(|character| !character.is_whitespace())
    {
        return None;
    }
    let state = match marker {
        ' ' => CheckboxState::Open,
        'x' | 'X' => CheckboxState::Done,
        '/' => CheckboxState::Skipped,
        _ => CheckboxState::Custom,
    };
    Some(MarkdownCheckbox {
        raw_marker: marker.to_string(),
        state,
    })
}

fn list_body(raw_item: &str) -> Option<&str> {
    let trimmed = raw_item.trim_start_matches([' ', '\t']);
    let mut characters = trimmed.char_indices();
    let (_, first) = characters.next()?;
    let marker_end = if matches!(first, '-' | '+' | '*') {
        first.len_utf8()
    } else if first.is_ascii_digit() {
        characters
            .find(|(_, character)| matches!(character, '.' | ')'))
            .map(|(offset, character)| offset + character.len_utf8())?
    } else {
        return None;
    };
    let remainder = trimmed.get(marker_end..)?;
    if !remainder.starts_with(char::is_whitespace) {
        return None;
    }
    Some(remainder.trim_start_matches(char::is_whitespace))
}

fn strip_checkbox<'a>(plain: &'a str, checkbox: Option<&MarkdownCheckbox>) -> &'a str {
    if checkbox.is_none() || !plain.starts_with('[') {
        return plain;
    }
    let Some(close) = plain.find(']') else {
        return plain;
    };
    plain.get(close + 1..).unwrap_or_default().trim_start()
}

fn leading_key(plain: &str) -> Option<String> {
    let (candidate, _) = plain.split_once(':')?;
    let key = candidate.trim();
    if key.is_empty()
        || !key
            .chars()
            .all(|character| character.is_alphanumeric() || matches!(character, '-' | '_'))
    {
        return None;
    }
    Some(key.to_owned())
}

fn relationship_kind(key: &str) -> Option<RelationshipKind> {
    RELATIONSHIP_KINDS
        .iter()
        .find(|(name, _)| *name == key)
        .map(|(_, kind)| *kind)
}
