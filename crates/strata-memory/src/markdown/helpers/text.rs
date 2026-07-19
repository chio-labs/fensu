//! Markdown parser options and normalized plain-text rendering.

use pulldown_cmark::{Event, Options, Parser, TagEnd};

pub(crate) fn parser_options() -> Options {
    Options::ENABLE_TABLES
        | Options::ENABLE_FOOTNOTES
        | Options::ENABLE_STRIKETHROUGH
        | Options::ENABLE_TASKLISTS
        | Options::ENABLE_HEADING_ATTRIBUTES
        | Options::ENABLE_GFM
        | Options::ENABLE_DEFINITION_LIST
}

pub(crate) fn plain_text(source: &str) -> String {
    let parser = Parser::new_ext(source, parser_options()).into_offset_iter();
    let mut rendered = String::new();
    for (event, _) in parser {
        match event {
            Event::Text(value)
            | Event::Code(value)
            | Event::InlineMath(value)
            | Event::DisplayMath(value)
            | Event::FootnoteReference(value) => rendered.push_str(&value),
            Event::SoftBreak | Event::HardBreak => push_separator(&mut rendered, '\n'),
            Event::TaskListMarker(checked) => {
                rendered.push_str(if checked { "[x] " } else { "[ ] " });
            }
            Event::Rule => push_separator(&mut rendered, '\n'),
            Event::End(
                TagEnd::Paragraph
                | TagEnd::Heading(_)
                | TagEnd::Item
                | TagEnd::TableHead
                | TagEnd::TableRow
                | TagEnd::CodeBlock,
            ) => push_separator(&mut rendered, '\n'),
            Event::Start(_) | Event::End(_) | Event::Html(_) | Event::InlineHtml(_) => {}
        }
    }
    normalize_lines(&rendered)
}

fn push_separator(target: &mut String, separator: char) {
    if !target.is_empty() && !target.ends_with(separator) {
        target.push(separator);
    }
}

fn normalize_lines(value: &str) -> String {
    let mut normalized = String::new();
    for line in value.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            push_separator(&mut normalized, '\n');
        } else {
            if !normalized.is_empty() && !normalized.ends_with(['\n', ' ']) {
                normalized.push(' ');
            }
            normalized.push_str(trimmed);
            normalized.push('\n');
        }
    }
    normalized.trim().to_owned()
}
