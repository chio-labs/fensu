use std::collections::HashSet;

use crate::configuration::_helpers::validation::required_strings;

pub(crate) fn validate_test_scopes(value: Option<&toml::Value>) -> Result<(), String> {
    let Some(value) = value else {
        return Ok(());
    };
    let scopes = required_strings(Some(value), "test_scopes")?;
    if scopes.is_empty() {
        return Err("Config key test_scopes must not be empty.".to_owned());
    }
    if scopes.iter().collect::<HashSet<_>>().len() != scopes.len() {
        return Err("Config key test_scopes must not contain duplicates.".to_owned());
    }
    for scope in &scopes {
        if !valid_test_scope(scope) {
            return Err(format!(
                "Config key test_scopes must contain single lowercase path segments: {scope:?}."
            ));
        }
    }
    Ok(())
}

fn valid_test_scope(scope: &str) -> bool {
    let bytes = scope.as_bytes();
    !scope.is_empty()
        && bytes[0].is_ascii_lowercase()
        && !scope.ends_with(['_', '-'])
        && !bytes
            .windows(2)
            .any(|pair| matches!(pair[0], b'_' | b'-') && matches!(pair[1], b'_' | b'-'))
        && bytes.iter().all(|byte| {
            byte.is_ascii_lowercase() || byte.is_ascii_digit() || *byte == b'_' || *byte == b'-'
        })
}
