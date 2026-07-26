//! Parse and normalise initialisation arguments.

use crate::models::InitOptions;

pub(crate) fn parse_init(arguments: &[String]) -> Result<InitOptions, String> {
    let mut options = InitOptions::default();
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--yes" => options.yes = true,
            "--skills" => options.skills = Some(true),
            "--no-skills" => options.skills = Some(false),
            "--help" | "-h" => options.help = true,
            "--name" => {
                index += 1;
                options.name = Some(required_value(arguments, index, "--name")?);
            }
            "--root" | "--tests" | "--tooling" => {
                let option = arguments[index].clone();
                let mut values = Vec::new();
                while index + 1 < arguments.len() && !arguments[index + 1].starts_with('-') {
                    index += 1;
                    values.push(arguments[index].clone());
                }
                if values.is_empty() {
                    return Err(format!(
                        "fensu init: error: argument {option}: expected at least one argument"
                    ));
                }
                match option.as_str() {
                    "--root" => options.roots.extend(values),
                    "--tests" => options.tests.extend(values),
                    _ => options.tooling.extend(values),
                }
            }
            value => {
                return Err(format!(
                    "usage: fensu init ...\nfensu init: error: unrecognized arguments: {value}"
                ))
            }
        }
        index += 1;
    }
    Ok(options)
}

fn required_value(arguments: &[String], index: usize, option: &str) -> Result<String, String> {
    arguments
        .get(index)
        .filter(|value| !value.starts_with('-'))
        .cloned()
        .ok_or_else(|| format!("fensu init: error: argument {option}: expected one argument"))
}

pub(crate) fn requests_scopes(options: &InitOptions) -> bool {
    !options.roots.is_empty()
        || !options.tests.is_empty()
        || !options.tooling.is_empty()
        || options.name.is_some()
}

pub(crate) fn normalize_name(value: &str) -> Result<String, String> {
    let mut result = String::new();
    for character in value.trim().chars() {
        if character.is_ascii_alphanumeric() || character == '_' {
            result.push(character.to_ascii_lowercase());
        } else if !result.ends_with('_') {
            result.push('_');
        }
    }
    let result = result.trim_matches('_').to_owned();
    if result.is_empty() {
        return Err(format!(
            "Project name cannot be normalized to a Python identifier: {value:?}."
        ));
    }
    Ok(
        if result.starts_with(|character: char| character.is_ascii_digit()) {
            format!("_{result}")
        } else {
            result
        },
    )
}
