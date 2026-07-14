//! Text helpers matching CPython string semantics.

pub(crate) fn python_trim(text: &str) -> &str {
    text.trim_matches(is_python_space)
}

pub(crate) fn char_column(source: &str, line_start: usize, offset: usize) -> u32 {
    let clamped_start = line_start.min(source.len());
    let clamped_offset = offset.min(source.len()).max(clamped_start);
    let count = source
        .get(clamped_start..clamped_offset)
        .map(|prefix| prefix.chars().count())
        .unwrap_or_default();
    u32::try_from(count).unwrap_or(u32::MAX)
}

fn is_python_space(character: char) -> bool {
    character.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&character)
}
