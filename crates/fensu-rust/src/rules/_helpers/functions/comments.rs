//! Lexical comment discovery without interpreting literal contents as source.

pub(crate) struct Comment {
    pub(crate) line: usize,
    pub(crate) end_line: usize,
    pub(crate) is_doc: bool,
    pub(crate) is_line: bool,
}

pub(crate) fn scan(source: &str) -> Vec<Comment> {
    let mut comments: Vec<Comment> = Vec::new();
    let mut offset = 0;
    let mut line = 1;
    while offset < source.len() {
        let remaining = &source[offset..];
        let length = token_length(remaining);
        let token = &remaining[..length];
        let end_line = line + token.bytes().filter(|byte| *byte == b'\n').count();
        if token.starts_with("//") || token.starts_with("/*") {
            comments.push(Comment {
                line,
                end_line,
                is_line: token.starts_with("//"),
                is_doc: token.starts_with("//!")
                    || (token.starts_with("///") && !token.starts_with("////"))
                    || token.starts_with("/*!")
                    || (token.starts_with("/**")
                        && !token.starts_with("/***")
                        && !token.starts_with("/**/")),
            });
        }
        line = end_line;
        offset += length;
    }
    comments
}

fn token_length(source: &str) -> usize {
    if source.starts_with("//") {
        return source.find('\n').unwrap_or(source.len());
    }
    if source.starts_with("/*") {
        return block_length(source);
    }
    if let Some(length) = raw_length(source) {
        return length;
    }
    for prefix in ["\"", "b\"", "c\""] {
        if source.starts_with(prefix) {
            return quoted_length(source, prefix.len(), b'"');
        }
    }
    if source.starts_with("b'") {
        return quoted_length(source, 2, b'\'');
    }
    if let Some(body) = source.strip_prefix('\'') {
        let identifier = identifier_length(body);
        if identifier > 0 && body.as_bytes().get(identifier) != Some(&b'\'') {
            return 1 + identifier;
        }
        return quoted_length(source, 1, b'\'');
    }
    let identifier = identifier_length(source);
    if identifier > 0 {
        return identifier;
    }
    source.chars().next().map_or(0, char::len_utf8)
}

fn identifier_length(source: &str) -> usize {
    let mut chars = source.char_indices();
    let Some((_, first)) = chars.next() else {
        return 0;
    };
    if first != '_' && !unicode_ident::is_xid_start(first) {
        return 0;
    }
    chars
        .find(|(_, character)| !unicode_ident::is_xid_continue(*character))
        .map_or(source.len(), |(index, _)| index)
}

fn quoted_length(source: &str, start: usize, delimiter: u8) -> usize {
    let mut escaped = false;
    for (index, byte) in source.bytes().enumerate().skip(start) {
        if escaped {
            escaped = false;
        } else if byte == b'\\' {
            escaped = true;
        } else if byte == delimiter {
            return index + 1;
        }
    }
    source.len()
}

fn raw_length(source: &str) -> Option<usize> {
    let prefix = ["br", "cr", "r"]
        .into_iter()
        .find(|prefix| source.starts_with(prefix))?;
    let hashes = source[prefix.len()..]
        .bytes()
        .take_while(|byte| *byte == b'#')
        .count();
    let quote = prefix.len() + hashes;
    if source.as_bytes().get(quote) != Some(&b'"') {
        return None;
    }
    let ending = format!("\"{}", "#".repeat(hashes));
    Some(
        source[quote + 1..]
            .find(&ending)
            .map_or(source.len(), |index| quote + 1 + index + ending.len()),
    )
}

fn block_length(source: &str) -> usize {
    let bytes = source.as_bytes();
    let mut depth = 1;
    let mut index = 2;
    while index + 1 < bytes.len() {
        match &bytes[index..index + 2] {
            b"/*" => depth += 1,
            b"*/" => depth -= 1,
            _ => {
                index += 1;
                continue;
            }
        }
        index += 2;
        if depth == 0 {
            return index;
        }
    }
    source.len()
}
