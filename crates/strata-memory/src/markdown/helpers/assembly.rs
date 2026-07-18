//! Assembly of independent Markdown and Obsidian extraction phases.

use crate::markdown::helpers::{blocks, headings, line_index::LineIndex, links, lists, obsidian};
use crate::markdown::models::{MarkdownLink, MarkdownListItem, MarkdownSection, ParsedMarkdown};

pub(crate) fn parse(source: &str) -> ParsedMarkdown {
    let index = LineIndex::new(source);
    let headings = headings::extract(source, &index);
    let title = headings::title(&headings);
    let (preamble_raw_markdown, preamble_plain_text) = headings::preamble(source, &headings);
    let sections = headings::sections(source, &headings, &index);
    let mut list_items = lists::extract(source, &index);
    let preamble_bounds = headings::preamble_bounds(source.len(), &headings);
    attach_list_context(&mut list_items, &sections, preamble_bounds);
    let code_blocks = blocks::extract(source, &index);
    let mut extracted_links = links::extract(source, &index);
    let (obsidian_links, tags) = obsidian::extract(source, &index);
    extracted_links.extend(obsidian_links);
    normalize_links(&mut extracted_links, &list_items);
    ParsedMarkdown {
        raw_markdown: source.to_owned(),
        plain_text: crate::markdown::helpers::text::plain_text(source),
        title,
        preamble_raw_markdown,
        preamble_plain_text,
        headings,
        sections,
        list_items,
        code_blocks,
        links: extracted_links,
        tags,
    }
}

fn attach_list_context(
    items: &mut [MarkdownListItem],
    sections: &[MarkdownSection],
    preamble_bounds: (usize, usize),
) {
    for item in items {
        let offset = item.source_range.start_byte;
        item.section_ordinal = sections
            .iter()
            .find(|section| {
                section.source_range.start_byte <= offset && offset < section.source_range.end_byte
            })
            .map(|section| section.ordinal)
            .or_else(|| (preamble_bounds.0 <= offset && offset < preamble_bounds.1).then_some(0));
    }
}

fn normalize_links(links: &mut Vec<MarkdownLink>, items: &[MarkdownListItem]) {
    links.sort_by_key(|link| (link.source_range.start_byte, link.source_range.end_byte));
    links.dedup_by(|right, left| {
        right.source_range.start_byte == left.source_range.start_byte
            && right.source_range.end_byte == left.source_range.end_byte
            && right.syntax_kind == left.syntax_kind
    });
    for (position, link) in links.iter_mut().enumerate() {
        link.ordinal = position + 1;
        let owner = items
            .iter()
            .filter(|item| {
                item.source_range.start_byte <= link.source_range.start_byte
                    && link.source_range.end_byte <= item.source_range.end_byte
            })
            .max_by_key(|item| (item.nesting_depth, item.source_range.start_byte));
        if let Some(item) = owner {
            link.list_item_ordinal = Some(item.ordinal);
            link.relationship_kind = item.relationship_kind;
        }
    }
}
