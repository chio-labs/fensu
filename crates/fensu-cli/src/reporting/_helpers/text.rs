//! Wrap remediation text and read excerpted source lines.

use std::fs;
use std::path::Path;

use crate::reporting::constants::{DIM, HELP_CONTINUATION, REPORT_LINE_WIDTH, RESET};

pub(crate) fn wrapped_help(remediation: &str, label: &str, color: bool) -> Vec<String> {
    let prefix = format!("  = {label}: ");
    let mut wrapped = wrap_text(remediation, &prefix, HELP_CONTINUATION);
    if color {
        let first = wrapped[0].strip_prefix(&prefix).unwrap_or(&wrapped[0]);
        wrapped[0] = format!("  {DIM}= {label}:{RESET} {first}");
    }
    wrapped
}

fn wrap_text(text: &str, initial_indent: &str, subsequent_indent: &str) -> Vec<String> {
    let mut lines: Vec<String> = Vec::new();
    let mut line = initial_indent.to_owned();
    let mut line_len = initial_indent.chars().count();
    let mut has_content = false;
    for word in text.split_whitespace() {
        let separator_len = usize::from(has_content);
        let word_len = word.chars().count();
        if line_len + separator_len + word_len <= REPORT_LINE_WIDTH {
            if has_content {
                line.push(' ');
                line_len += 1;
            }
            line.push_str(word);
            line_len += word_len;
            has_content = true;
            continue;
        }
        if has_content {
            lines.push(line);
            line = subsequent_indent.to_owned();
            line_len = subsequent_indent.chars().count();
            has_content = false;
        }
        let mut chunks = word.chars();
        loop {
            let capacity = REPORT_LINE_WIDTH.saturating_sub(line_len);
            let chunk: String = chunks.by_ref().take(capacity).collect();
            if chunk.is_empty() {
                break;
            }
            line.push_str(&chunk);
            line_len += chunk.chars().count();
            has_content = true;
            if line_len < REPORT_LINE_WIDTH {
                break;
            }
            lines.push(line);
            line = subsequent_indent.to_owned();
            line_len = subsequent_indent.chars().count();
            has_content = false;
        }
    }
    if has_content || lines.is_empty() {
        lines.push(line);
    }
    lines
}

pub(crate) fn source_line(path: &Path, line: u32) -> Option<String> {
    let Ok(source) = fs::read_to_string(path) else {
        return None;
    };
    source
        .lines()
        .nth(line.saturating_sub(1) as usize)
        .map(str::to_owned)
}
