//! Frozen heading text and generated-slug matching precedence.

use crate::markdown::models::{MarkdownHeading, ParsedMarkdown};

pub(crate) fn resolve<'markdown>(
    markdown: &'markdown ParsedMarkdown,
    fragment: &str,
) -> Vec<&'markdown MarkdownHeading> {
    let exact_text = matching(markdown, |heading| heading.text == fragment);
    if !exact_text.is_empty() {
        return exact_text;
    }
    let exact_slug = matching(markdown, |heading| heading.slug == fragment);
    if !exact_slug.is_empty() {
        return exact_slug;
    }
    matching(markdown, |heading| {
        heading.text.eq_ignore_ascii_case(fragment) || heading.slug.eq_ignore_ascii_case(fragment)
    })
}

pub(crate) fn section_ordinal(
    markdown: &ParsedMarkdown,
    heading: &MarkdownHeading,
) -> Option<usize> {
    markdown
        .sections
        .iter()
        .find(|section| section.heading_ordinal == heading.ordinal)
        .map(|section| section.ordinal)
}

fn matching<F>(markdown: &ParsedMarkdown, predicate: F) -> Vec<&MarkdownHeading>
where
    F: Fn(&MarkdownHeading) -> bool,
{
    markdown
        .headings
        .iter()
        .filter(|heading| predicate(heading))
        .collect()
}
