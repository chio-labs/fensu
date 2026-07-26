pub(crate) fn validate_nested_roots(roots: Vec<String>) -> Result<(), String> {
    for (index, first) in roots.iter().enumerate() {
        let first_parts = first.split('/').collect::<Vec<_>>();
        for second in roots.iter().skip(index + 1) {
            let second_parts = second.split('/').collect::<Vec<_>>();
            let length = first_parts.len().min(second_parts.len());
            if first_parts[..length] != second_parts[..length] {
                continue;
            }
            return Err(nested_roots_error(
                first,
                second,
                first_parts.len() <= second_parts.len(),
            ));
        }
    }
    Ok(())
}

fn nested_roots_error(first: &str, second: &str, first_is_outer: bool) -> String {
    let (outer, inner) = if first_is_outer {
        (first, second)
    } else {
        (second, first)
    };
    if outer == inner {
        return format!("Config key roots must not contain duplicate paths: {outer:?}.");
    }
    format!("Config key roots must not contain nested paths: {outer:?} contains {inner:?}.")
}
