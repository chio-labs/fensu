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
    let mut rendered = TextBuffer::default();
    for (event, _) in parser {
        match event {
            Event::Text(value)
            | Event::Code(value)
            | Event::InlineMath(value)
            | Event::DisplayMath(value)
            | Event::FootnoteReference(value) => rendered.value.push_str(&value),
            Event::SoftBreak | Event::HardBreak => rendered.push_separator('\n'),
            Event::TaskListMarker(checked) => {
                rendered
                    .value
                    .push_str(if checked { "[x] " } else { "[ ] " });
            }
            Event::Rule => rendered.push_separator('\n'),
            Event::End(
                TagEnd::Paragraph
                | TagEnd::Heading(_)
                | TagEnd::Item
                | TagEnd::TableHead
                | TagEnd::TableRow
                | TagEnd::CodeBlock,
            ) => rendered.push_separator('\n'),
            Event::Start(_) | Event::End(_) | Event::Html(_) | Event::InlineHtml(_) => {}
        }
    }
    normalize_lines(&rendered.value)
}

#[derive(Default)]
struct TextBuffer {
    value: String,
}

impl TextBuffer {
    fn push_separator(&mut self, separator: char) {
        if !self.value.is_empty() && !self.value.ends_with(separator) {
            self.value.push(separator);
        }
    }
}

fn normalize_lines(value: &str) -> String {
    let mut normalized = TextBuffer::default();
    for line in value.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            normalized.push_separator('\n');
        } else {
            if !normalized.value.is_empty() && !normalized.value.ends_with(['\n', ' ']) {
                normalized.value.push(' ');
            }
            normalized.value.push_str(trimmed);
            normalized.value.push('\n');
        }
    }
    normalized.value.trim().to_owned()
}
