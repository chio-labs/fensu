use crate::rules::models::NativeRuleContext;

const TESTS_PACKAGE: &str = "tests";

pub(super) fn quoted_strings(source: &str) -> Vec<(usize, String)> {
    let bytes = source.as_bytes();
    let mut values: Vec<(usize, String)> = Vec::new();
    let mut index = 0;
    while index < bytes.len() {
        let quote = bytes[index];
        if quote != b'\'' && quote != b'"' {
            index += 1;
            continue;
        }
        let start = index;
        index += 1;
        let value_start = index;
        while index < bytes.len() && bytes[index] != quote {
            index += if bytes[index] == b'\\' { 2 } else { 1 };
        }
        if index <= bytes.len() {
            values.push((
                start,
                source[value_start..index.min(bytes.len())].to_owned(),
            ));
        }
        index += 1;
    }
    values
}

pub(super) fn source_position(source: &str, offset: usize) -> (u32, u32) {
    let prefix = &source[..offset.min(source.len())];
    let line =
        u32::try_from(prefix.bytes().filter(|byte| *byte == b'\n').count() + 1).unwrap_or(u32::MAX);
    let column = u32::try_from(
        prefix
            .rsplit_once('\n')
            .map_or(prefix.len(), |item| item.1.len()),
    )
    .unwrap_or(u32::MAX);
    (line, column)
}

pub(super) fn project_module_literal(value: &str, context: &NativeRuleContext) -> bool {
    let roots = std::iter::once(context.package_name.as_str())
        .chain(std::iter::once(TESTS_PACKAGE))
        .chain(context.tooling_packages.iter().map(String::as_str));
    roots
        .into_iter()
        .any(|root| valid_project_module_literal(value, root))
}

fn valid_project_module_literal(value: &str, root: &str) -> bool {
    if !value.starts_with(&format!("{root}.")) {
        return false;
    }
    for part in value.split('.') {
        if part.is_empty()
            || !part
                .chars()
                .all(|character| character == '_' || character.is_ascii_alphanumeric())
        {
            return false;
        }
    }
    true
}
