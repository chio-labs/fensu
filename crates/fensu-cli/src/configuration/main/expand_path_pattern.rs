use crate::constants::{MAX_EXPANDED_PATH_PATTERNS, MIN_BRACE_ALTERNATIVES};

pub(crate) fn expand_path_pattern(pattern: &str) -> Result<Vec<String>, String> {
    let expansion_limit_error = || {
        format!(
            "Path glob expands to more than {MAX_EXPANDED_PATH_PATTERNS} alternatives: {pattern}."
        )
    };
    let mut pending: Vec<String> = vec![pattern.to_owned()];
    let mut expanded: Vec<String> = Vec::new();
    while let Some(candidate) = pending.pop() {
        let Some((start, end)) = group_bounds(&candidate, pattern)? else {
            expanded.push(candidate);
            if expanded.len() > MAX_EXPANDED_PATH_PATTERNS {
                return Err(expansion_limit_error());
            }
            continue;
        };
        let alternatives = group_alternatives(&candidate[start + 1..end], pattern)?;
        if pending.len() + expanded.len() + alternatives.len() > MAX_EXPANDED_PATH_PATTERNS {
            return Err(expansion_limit_error());
        }
        for alternative in alternatives.into_iter().rev() {
            pending.push(format!(
                "{}{}{}",
                &candidate[..start],
                alternative,
                &candidate[end + 1..]
            ));
        }
    }
    Ok(expanded)
}

fn group_bounds(candidate: &str, original: &str) -> Result<Option<(usize, usize)>, String> {
    let mut start = None;
    let mut depth = 0;
    for (index, character) in candidate.char_indices() {
        match character {
            '{' => {
                if start.is_none() {
                    start = Some(index);
                }
                depth += 1;
            }
            '}' => {
                if depth == 0 {
                    return Err(format!(
                        "Path glob contains an unmatched closing brace: {original}."
                    ));
                }
                depth -= 1;
                if depth == 0 {
                    return Ok(start.map(|start| (start, index)));
                }
            }
            _ => {}
        }
    }
    if start.is_some() {
        return Err(format!(
            "Path glob contains an unmatched opening brace: {original}."
        ));
    }
    Ok(None)
}

fn group_alternatives<'a>(group: &'a str, original: &str) -> Result<Vec<&'a str>, String> {
    let mut alternatives: Vec<&str> = Vec::new();
    let mut start = 0;
    let mut depth = 0;
    for (index, character) in group.char_indices() {
        match character {
            '{' => depth += 1,
            '}' => depth -= 1,
            ',' if depth == 0 => {
                alternatives.push(&group[start..index]);
                start = index + 1;
            }
            _ => {}
        }
    }
    alternatives.push(&group[start..]);
    if alternatives.len() < MIN_BRACE_ALTERNATIVES
        || alternatives
            .iter()
            .any(|alternative| alternative.is_empty())
    {
        return Err(format!(
            "Path glob brace groups must contain at least two non-empty alternatives: {original}."
        ));
    }
    Ok(alternatives)
}
