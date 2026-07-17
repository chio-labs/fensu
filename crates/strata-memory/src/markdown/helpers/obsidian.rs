//! Masked raw-source scanning for Obsidian links, embeds, tags, and bare URLs.

use std::ops::Range;

use pulldown_cmark::{Event, Parser, Tag};

use crate::markdown::constants::FRONTMATTER_DELIMITER;
use crate::markdown::helpers::line_index::LineIndex;
use crate::markdown::helpers::text;
use crate::markdown::models::{MarkdownLink, MarkdownTag};
use crate::markdown::types::LinkSyntaxKind;

pub(crate) fn extract(source: &str, index: &LineIndex) -> (Vec<MarkdownLink>, Vec<MarkdownTag>) {
    let mut mask = exclusion_mask(source);
    mask_frontmatter(source, &mut mask);
    mask_comments(source, &mut mask);
    let mut links = wikilinks(source, index, &mut mask);
    links.extend(bare_urls(source, index, &mask));
    let tags = tags(source, index, &mask);
    (links, tags)
}

fn exclusion_mask(source: &str) -> Vec<bool> {
    let parser = Parser::new_ext(source, text::parser_options()).into_offset_iter();
    let mut mask = vec![false; source.len()];
    for (event, range) in parser {
        if matches!(event, Event::Start(Tag::CodeBlock(_)) | Event::Code(_))
            || matches!(event, Event::Start(Tag::Link { .. }))
        {
            mark(&mut mask, range);
        }
    }
    mask
}

fn mask_frontmatter(source: &str, mask: &mut [bool]) {
    let first_end = source.find('\n').map_or(source.len(), |offset| offset + 1);
    let first = source
        .get(..first_end)
        .unwrap_or_default()
        .trim_end_matches(['\r', '\n']);
    if first != FRONTMATTER_DELIMITER {
        return;
    }
    let mut cursor = first_end;
    while cursor < source.len() {
        let next = source
            .get(cursor..)
            .and_then(|rest| rest.find('\n'))
            .map_or(source.len(), |offset| cursor + offset + 1);
        let line = source
            .get(cursor..next)
            .unwrap_or_default()
            .trim_end_matches(['\r', '\n']);
        if matches!(line, "---" | "...") {
            mark(mask, 0..next);
            return;
        }
        cursor = next;
    }
}

fn mask_comments(source: &str, mask: &mut [bool]) {
    let bytes = source.as_bytes();
    let mut cursor = 0;
    while cursor + 1 < bytes.len() {
        if !mask[cursor] && bytes[cursor] == b'%' && bytes[cursor + 1] == b'%' {
            let start = cursor;
            cursor += 2;
            while cursor + 1 < bytes.len()
                && (mask[cursor] || bytes[cursor] != b'%' || bytes[cursor + 1] != b'%')
            {
                cursor += 1;
            }
            cursor = (cursor + 2).min(bytes.len());
            mark(mask, start..cursor);
        } else {
            cursor += 1;
        }
    }
}

fn wikilinks(source: &str, index: &LineIndex, mask: &mut [bool]) -> Vec<MarkdownLink> {
    let bytes = source.as_bytes();
    let mut links = Vec::new();
    let mut cursor = 0;
    while cursor + 1 < bytes.len() {
        let embedded = bytes[cursor] == b'!'
            && cursor + 2 < bytes.len()
            && bytes[cursor + 1] == b'['
            && bytes[cursor + 2] == b'[';
        let opening =
            !mask[cursor] && ((bytes[cursor] == b'[' && bytes[cursor + 1] == b'[') || embedded);
        if !opening {
            cursor += 1;
            continue;
        }
        let body_start = cursor + if embedded { 3 } else { 2 };
        let Some(end) = wikilink_end(bytes, mask, body_start) else {
            cursor += 1;
            continue;
        };
        let range = cursor..end + 2;
        if let Some(link) = build_wikilink(source, index, range.clone(), body_start..end, embedded)
        {
            links.push(link);
            mark(mask, range.clone());
        }
        cursor = range.end;
    }
    links
}

fn wikilink_end(bytes: &[u8], mask: &[bool], mut cursor: usize) -> Option<usize> {
    while cursor + 1 < bytes.len() {
        if bytes[cursor] == b'\n' || bytes[cursor] == b'\r' || mask[cursor] {
            return None;
        }
        if bytes[cursor] == b']' && bytes[cursor + 1] == b']' {
            return Some(cursor);
        }
        cursor += 1;
    }
    None
}

fn build_wikilink(
    source: &str,
    index: &LineIndex,
    range: Range<usize>,
    body_range: Range<usize>,
    embedded: bool,
) -> Option<MarkdownLink> {
    let body = source.get(body_range)?.trim();
    let (destination, alias) = body
        .split_once('|')
        .map_or((body, None), |(target, display)| {
            (target.trim(), nonempty(display))
        });
    let (target, heading_fragment) = destination
        .split_once('#')
        .map_or((destination.trim(), None), |(document, heading)| {
            (document.trim(), nonempty(heading))
        });
    if target.is_empty() && heading_fragment.is_none() {
        return None;
    }
    Some(MarkdownLink {
        ordinal: 0,
        syntax_kind: if embedded {
            LinkSyntaxKind::Embed
        } else {
            LinkSyntaxKind::Wikilink
        },
        target: target.to_owned(),
        alias: alias.map(str::to_owned),
        display: alias.map(str::to_owned),
        heading_fragment: heading_fragment.map(str::to_owned),
        raw_source: source.get(range.clone()).unwrap_or_default().to_owned(),
        source_line: index.line_number(range.start),
        source_range: index.source_range(range),
        list_item_ordinal: None,
        relationship_kind: None,
    })
}

fn bare_urls(source: &str, index: &LineIndex, mask: &[bool]) -> Vec<MarkdownLink> {
    let mut links = Vec::new();
    for (start, _) in source.char_indices() {
        if mask[start] || !starts_url(source.get(start..).unwrap_or_default()) {
            continue;
        }
        if start > 0
            && source
                .get(..start)
                .and_then(|value| value.chars().next_back())
                .is_some_and(is_url_character)
        {
            continue;
        }
        let rest = source.get(start..).unwrap_or_default();
        let relative_end = rest
            .char_indices()
            .find(|(_, character)| {
                character.is_whitespace()
                    || matches!(character, '<' | '>' | '"' | '\'' | ')' | ']' | '}')
            })
            .map_or(rest.len(), |(offset, _)| offset);
        let candidate = rest.get(..relative_end).unwrap_or_default();
        let target = candidate.trim_end_matches(['.', ',', ';', ':', '!', '?']);
        let end = start + target.len();
        if end == start
            || mask
                .get(start..end)
                .is_some_and(|range| range.iter().any(|value| *value))
        {
            continue;
        }
        links.push(MarkdownLink {
            ordinal: 0,
            syntax_kind: LinkSyntaxKind::ExternalUrl,
            target: target.to_owned(),
            alias: None,
            display: Some(target.to_owned()),
            heading_fragment: None,
            raw_source: target.to_owned(),
            source_line: index.line_number(start),
            source_range: index.source_range(start..end),
            list_item_ordinal: None,
            relationship_kind: None,
        });
    }
    links
}

fn tags(source: &str, index: &LineIndex, mask: &[bool]) -> Vec<MarkdownTag> {
    let mut tags = Vec::new();
    for (start, character) in source.char_indices() {
        if character != '#' || mask[start] || !tag_boundary(source, start) {
            continue;
        }
        let content_start = start + character.len_utf8();
        let rest = source.get(content_start..).unwrap_or_default();
        let end_offset = rest
            .char_indices()
            .find(|(_, value)| !is_tag_character(*value))
            .map_or(rest.len(), |(offset, _)| offset);
        let name = rest.get(..end_offset).unwrap_or_default();
        if !valid_tag(name) {
            continue;
        }
        let end = content_start + name.len();
        tags.push(MarkdownTag {
            ordinal: tags.len() + 1,
            name: name.to_owned(),
            raw_source: source.get(start..end).unwrap_or_default().to_owned(),
            source_line: index.line_number(start),
            source_range: index.source_range(start..end),
        });
    }
    tags
}

fn mark(mask: &mut [bool], range: Range<usize>) {
    let end = range.end.min(mask.len());
    for value in mask.iter_mut().take(end).skip(range.start.min(end)) {
        *value = true;
    }
}

fn nonempty(value: &str) -> Option<&str> {
    let trimmed = value.trim();
    (!trimmed.is_empty()).then_some(trimmed)
}

fn starts_url(value: &str) -> bool {
    value.starts_with("https://") || value.starts_with("http://")
}

fn is_url_character(character: char) -> bool {
    character.is_alphanumeric() || matches!(character, '_' | '-' | '/')
}

fn tag_boundary(source: &str, start: usize) -> bool {
    source
        .get(..start)
        .and_then(|value| value.chars().next_back())
        .is_none_or(|character| !is_tag_character(character) && !matches!(character, '#' | '\\'))
}

fn is_tag_character(character: char) -> bool {
    character.is_alphanumeric() || matches!(character, '_' | '-' | '/')
}

fn valid_tag(name: &str) -> bool {
    !name.is_empty()
        && name
            .chars()
            .any(|character| !character.is_numeric() && character != '/')
        && !name.starts_with('/')
        && !name.ends_with('/')
        && !name.contains("//")
}
