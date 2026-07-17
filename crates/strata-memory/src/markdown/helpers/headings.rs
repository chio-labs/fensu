//! Heading, title, preamble, and section extraction.

use std::ops::Range;

use pulldown_cmark::{Event, HeadingLevel, Parser, Tag, TagEnd};

use crate::markdown::constants::{
    MAX_PHASE_IDENTIFIER_LENGTH, SEMANTIC_HEADING_ALIASES, SEMANTIC_HEADING_KINDS,
};
use crate::markdown::helpers::line_index::LineIndex;
use crate::markdown::helpers::text;
use crate::markdown::models::{MarkdownHeading, MarkdownSection};
use crate::markdown::types::SemanticHeadingKind;

#[derive(Debug)]
struct ActiveHeading {
    level: u8,
    text: String,
    range: Range<usize>,
}

pub(crate) fn extract(source: &str, index: &LineIndex) -> Vec<MarkdownHeading> {
    let parser = Parser::new_ext(source, text::parser_options()).into_offset_iter();
    let mut headings = Vec::new();
    let mut path: Vec<(u8, String)> = Vec::new();
    let mut active: Option<ActiveHeading> = None;
    for (event, range) in parser {
        match event {
            Event::Start(Tag::Heading { level, .. }) => {
                active = Some(ActiveHeading {
                    level: heading_level(level),
                    text: String::new(),
                    range,
                });
            }
            Event::Text(value)
            | Event::Code(value)
            | Event::InlineMath(value)
            | Event::DisplayMath(value)
            | Event::FootnoteReference(value) => {
                if let Some(heading) = active.as_mut() {
                    heading.text.push_str(&value);
                }
            }
            Event::SoftBreak | Event::HardBreak => {
                if let Some(heading) = active.as_mut() {
                    heading.text.push(' ');
                }
            }
            Event::End(TagEnd::Heading(_)) => {
                if let Some(heading) = active.take() {
                    headings.push(build_heading(
                        source,
                        index,
                        &mut path,
                        heading,
                        headings.len(),
                    ));
                }
            }
            _ => {}
        }
    }
    headings
}

pub(crate) fn title(headings: &[MarkdownHeading]) -> Option<String> {
    headings
        .iter()
        .find(|heading| heading.level == 1)
        .filter(|heading| !heading.text.is_empty())
        .map(|heading| heading.text.clone())
}

pub(crate) fn preamble(source: &str, headings: &[MarkdownHeading]) -> (String, String) {
    let title = headings.iter().find(|heading| heading.level == 1);
    let start = title.map_or(0, |heading| heading.source_range.end_byte);
    let end = headings
        .iter()
        .find(|heading| heading.source_range.start_byte >= start && heading.level > 1)
        .map_or(source.len(), |heading| heading.source_range.start_byte);
    let raw = source.get(start..end).unwrap_or_default().to_owned();
    let plain = text::plain_text(&raw);
    (raw, plain)
}

pub(crate) fn sections(
    source: &str,
    headings: &[MarkdownHeading],
    index: &LineIndex,
) -> Vec<MarkdownSection> {
    let title_ordinal = headings
        .iter()
        .find(|heading| heading.level == 1)
        .map(|h| h.ordinal);
    let mut sections = Vec::new();
    for (position, heading) in headings.iter().enumerate() {
        if Some(heading.ordinal) == title_ordinal {
            continue;
        }
        let end = headings
            .get(position + 1)
            .map_or(source.len(), |next| next.source_range.start_byte);
        let range = heading.source_range.start_byte..end;
        let raw = source.get(range.clone()).unwrap_or_default().to_owned();
        sections.push(MarkdownSection {
            ordinal: sections.len() + 1,
            heading_ordinal: heading.ordinal,
            heading_path: heading.heading_path.clone(),
            plain_text: text::plain_text(&raw),
            raw_markdown: raw,
            source_range: index.source_range(range),
        });
    }
    sections
}

fn build_heading(
    source: &str,
    index: &LineIndex,
    path: &mut Vec<(u8, String)>,
    active: ActiveHeading,
    prior_count: usize,
) -> MarkdownHeading {
    let heading_text = active.text.trim().to_owned();
    while path.last().is_some_and(|(level, _)| *level >= active.level) {
        let _ = path.pop();
    }
    path.push((active.level, heading_text.clone()));
    let (semantic_kind, phase_identifier, phase_title) = semantic_metadata(&heading_text);
    MarkdownHeading {
        level: active.level,
        text: heading_text.clone(),
        ordinal: prior_count + 1,
        slug: slug(&heading_text),
        heading_path: path.iter().map(|(_, text)| text.clone()).collect(),
        raw_source: source
            .get(active.range.clone())
            .unwrap_or_default()
            .to_owned(),
        source_range: index.source_range(active.range),
        semantic_kind,
        phase_identifier,
        phase_title,
    }
}

fn semantic_metadata(
    heading: &str,
) -> (Option<SemanticHeadingKind>, Option<String>, Option<String>) {
    let normalized = slug(heading);
    let recognized = SEMANTIC_HEADING_KINDS
        .iter()
        .chain(SEMANTIC_HEADING_ALIASES)
        .find(|(name, _)| *name == normalized)
        .map(|(_, kind)| *kind);
    let Some((phase_kind, remainder)) = phase_prefix(heading) else {
        return (recognized, None, None);
    };
    let (identifier, title) = phase_parts(remainder);
    (Some(phase_kind), identifier, title)
}

fn phase_prefix(heading: &str) -> Option<(SemanticHeadingKind, &str)> {
    let mut parts = heading.splitn(2, char::is_whitespace);
    let prefix = parts
        .next()?
        .trim_matches(|character: char| !character.is_alphanumeric());
    let remainder = parts.next().unwrap_or_default().trim();
    SEMANTIC_HEADING_KINDS
        .iter()
        .find(|(name, kind)| {
            matches!(
                kind,
                SemanticHeadingKind::Phase
                    | SemanticHeadingKind::Stage
                    | SemanticHeadingKind::Milestone
                    | SemanticHeadingKind::Checkpoint
            ) && prefix.eq_ignore_ascii_case(name)
        })
        .map(|(_, kind)| (*kind, remainder))
}

fn phase_parts(remainder: &str) -> (Option<String>, Option<String>) {
    let boundary = remainder
        .char_indices()
        .find(|(_, character)| character.is_whitespace() || matches!(character, ':' | '-'))
        .map_or(remainder.len(), |(offset, _)| offset);
    let candidate = remainder
        .get(..boundary)
        .unwrap_or_default()
        .trim_matches(|character: char| !character.is_ascii_alphanumeric());
    if candidate.len() > MAX_PHASE_IDENTIFIER_LENGTH
        || !candidate
            .chars()
            .all(|character| character.is_ascii_alphanumeric())
        || !candidate
            .chars()
            .any(|character| character.is_ascii_digit())
    {
        return (None, None);
    }
    let title = remainder
        .get(boundary..)
        .unwrap_or_default()
        .trim_start_matches(|character: char| {
            character.is_whitespace() || matches!(character, ':' | '-')
        })
        .trim();
    (
        Some(candidate.to_owned()),
        (!title.is_empty()).then(|| title.to_owned()),
    )
}

fn slug(value: &str) -> String {
    let mut slug = String::new();
    let mut separator_pending = false;
    for character in value.chars() {
        if character.is_alphanumeric() {
            if separator_pending && !slug.is_empty() {
                slug.push('-');
            }
            for lowercase in character.to_lowercase() {
                slug.push(lowercase);
            }
            separator_pending = false;
        } else if character.is_whitespace() || matches!(character, '-' | '_') {
            separator_pending = true;
        }
    }
    slug
}

fn heading_level(level: HeadingLevel) -> u8 {
    match level {
        HeadingLevel::H1 => 1,
        HeadingLevel::H2 => 2,
        HeadingLevel::H3 => 3,
        HeadingLevel::H4 => 4,
        HeadingLevel::H5 => 5,
        HeadingLevel::H6 => 6,
    }
}
