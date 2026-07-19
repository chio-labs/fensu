//! Case-sensitive Python fnmatch semantics for function contract names.

#[derive(Debug, Eq, PartialEq)]
enum GlobToken {
    Star,
    Any,
    Literal(char),
    Class(CharacterClass),
}

#[derive(Debug, Eq, PartialEq)]
enum CharacterClass {
    Any,
    Never,
    Members {
        negated: bool,
        literals: Vec<char>,
        ranges: Vec<(char, char)>,
    },
}

impl CharacterClass {
    fn matches(&self, character: char) -> bool {
        match self {
            Self::Any => true,
            Self::Never => false,
            Self::Members {
                negated,
                literals,
                ranges,
            } => {
                let included: bool = literals.contains(&character)
                    || ranges
                        .iter()
                        .any(|(start, end)| *start <= character && character <= *end);
                included != *negated
            }
        }
    }
}

pub(crate) fn fnmatchcase(name: &str, pattern: &str) -> bool {
    let tokens: Vec<GlobToken> = glob_tokens(pattern);
    let characters: Vec<char> = name.chars().collect();
    let mut matched: Vec<Vec<bool>> = vec![vec![false; characters.len() + 1]; tokens.len() + 1];
    matched[0][0] = true;
    for (token_index, token) in tokens.iter().enumerate() {
        for character_index in 0..=characters.len() {
            matched[token_index + 1][character_index] = match token {
                GlobToken::Star => {
                    matched[token_index][character_index]
                        || (character_index > 0 && matched[token_index + 1][character_index - 1])
                }
                GlobToken::Any => character_index > 0 && matched[token_index][character_index - 1],
                GlobToken::Literal(expected) => {
                    character_index > 0
                        && matched[token_index][character_index - 1]
                        && characters[character_index - 1] == *expected
                }
                GlobToken::Class(class) => {
                    character_index > 0
                        && matched[token_index][character_index - 1]
                        && class.matches(characters[character_index - 1])
                }
            };
        }
    }
    matched[tokens.len()][characters.len()]
}

fn glob_tokens(pattern: &str) -> Vec<GlobToken> {
    let characters: Vec<char> = pattern.chars().collect();
    let mut tokens: Vec<GlobToken> = Vec::new();
    let mut index: usize = 0;
    while index < characters.len() {
        match characters[index] {
            '*' => {
                if tokens.last() != Some(&GlobToken::Star) {
                    tokens.push(GlobToken::Star);
                }
                index += 1;
            }
            '?' => {
                tokens.push(GlobToken::Any);
                index += 1;
            }
            '[' => {
                let start: usize = index + 1;
                let mut end: usize = start;
                if end < characters.len() && characters[end] == '!' {
                    end += 1;
                }
                if end < characters.len() && characters[end] == ']' {
                    end += 1;
                }
                while end < characters.len() && characters[end] != ']' {
                    end += 1;
                }
                if end == characters.len() {
                    tokens.push(GlobToken::Literal('['));
                    index += 1;
                } else {
                    tokens.push(GlobToken::Class(character_class(&characters[start..end])));
                    index = end + 1;
                }
            }
            literal => {
                tokens.push(GlobToken::Literal(literal));
                index += 1;
            }
        }
    }
    tokens
}

fn character_class(content: &[char]) -> CharacterClass {
    let mut chunks: Vec<Vec<char>> = class_chunks(content);
    let flattened: Vec<char> = chunks
        .iter()
        .enumerate()
        .flat_map(|(index, chunk)| {
            let separator = (index > 0).then_some('-');
            separator.into_iter().chain(chunk.iter().copied())
        })
        .collect();
    if flattened.is_empty() {
        return CharacterClass::Never;
    }
    if flattened == ['!'] {
        return CharacterClass::Any;
    }
    let negated: bool = flattened.first() == Some(&'!');
    if negated {
        chunks[0].remove(0);
    }
    let literals: Vec<char> = chunks.iter().flatten().copied().collect();
    let ranges: Vec<(char, char)> = chunks
        .windows(2)
        .filter_map(|pair| Some((*pair[0].last()?, *pair[1].first()?)))
        .collect();
    CharacterClass::Members {
        negated,
        literals,
        ranges,
    }
}

fn class_chunks(content: &[char]) -> Vec<Vec<char>> {
    if !content.contains(&'-') {
        return vec![content.to_vec()];
    }
    let mut chunks: Vec<Vec<char>> = Vec::new();
    let mut start: usize = 0;
    let mut search: usize = if content.first() == Some(&'!') { 2 } else { 1 };
    while let Some(relative) = content[search.min(content.len())..]
        .iter()
        .position(|character| *character == '-')
    {
        let hyphen: usize = search + relative;
        chunks.push(content[start..hyphen].to_vec());
        start = hyphen + 1;
        search = (hyphen + 3).min(content.len());
    }
    if start < content.len() {
        chunks.push(content[start..].to_vec());
    } else if let Some(last) = chunks.last_mut() {
        last.push('-');
    }
    for index in (1..chunks.len()).rev() {
        if chunks[index - 1].last() > chunks[index].first() {
            let mut replacement: Vec<char> =
                chunks[index - 1][..chunks[index - 1].len().saturating_sub(1)].to_vec();
            replacement.extend_from_slice(&chunks[index][1..]);
            chunks[index - 1] = replacement;
            chunks.remove(index);
        }
    }
    chunks
}
