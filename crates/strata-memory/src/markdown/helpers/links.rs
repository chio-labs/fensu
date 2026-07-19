//! Ordinary Markdown link extraction.

use std::ops::Range;

use pulldown_cmark::{Event, LinkType, Parser, Tag, TagEnd};

use crate::markdown::helpers::line_index::LineIndex;
use crate::markdown::helpers::text;
use crate::markdown::models::MarkdownLink;
use crate::markdown::types::LinkSyntaxKind;

#[derive(Debug)]
struct ActiveLink {
    target: String,
    display: String,
    link_type: LinkType,
    range: Range<usize>,
}

pub(crate) fn extract(source: &str, index: &LineIndex) -> Vec<MarkdownLink> {
    let parser = Parser::new_ext(source, text::parser_options()).into_offset_iter();
    let mut links = Vec::new();
    let mut active: Option<ActiveLink> = None;
    for (event, range) in parser {
        match event {
            Event::Start(Tag::Link {
                link_type,
                dest_url,
                ..
            }) => {
                active = Some(ActiveLink {
                    target: dest_url.into_string(),
                    display: String::new(),
                    link_type,
                    range,
                });
            }
            Event::Text(value)
            | Event::Code(value)
            | Event::InlineMath(value)
            | Event::DisplayMath(value)
            | Event::FootnoteReference(value) => {
                if let Some(link) = active.as_mut() {
                    link.display.push_str(&value);
                }
            }
            Event::SoftBreak | Event::HardBreak => {
                if let Some(link) = active.as_mut() {
                    link.display.push(' ');
                }
            }
            Event::End(TagEnd::Link) => {
                if let Some(link) = active.take() {
                    links.push(build_link(source, index, link, links.len()));
                }
            }
            _ => {}
        }
    }
    links
}

fn build_link(
    source: &str,
    index: &LineIndex,
    link: ActiveLink,
    prior_count: usize,
) -> MarkdownLink {
    let external = is_external(&link.target);
    let (target, heading_fragment) = if external {
        (link.target, None)
    } else {
        split_fragment(&link.target)
    };
    let display = link.display.trim();
    MarkdownLink {
        ordinal: prior_count + 1,
        syntax_kind: if external || matches!(link.link_type, LinkType::Autolink | LinkType::Email) {
            LinkSyntaxKind::ExternalUrl
        } else {
            LinkSyntaxKind::Markdown
        },
        target,
        alias: None,
        display: (!display.is_empty()).then(|| display.to_owned()),
        heading_fragment,
        raw_source: source
            .get(link.range.clone())
            .unwrap_or_default()
            .to_owned(),
        source_line: index.line_number(link.range.start),
        source_range: index.source_range(link.range),
        list_item_ordinal: None,
        relationship_kind: None,
    }
}

fn split_fragment(target: &str) -> (String, Option<String>) {
    let Some((document, fragment)) = target.split_once('#') else {
        return (target.to_owned(), None);
    };
    (
        document.to_owned(),
        (!fragment.is_empty()).then(|| fragment.to_owned()),
    )
}

fn is_external(target: &str) -> bool {
    if target.starts_with("//") {
        return true;
    }
    let Some((scheme, _)) = target.split_once(':') else {
        return false;
    };
    !scheme.is_empty()
        && scheme.chars().all(|character| {
            character.is_ascii_alphanumeric() || matches!(character, '+' | '-' | '.')
        })
}
