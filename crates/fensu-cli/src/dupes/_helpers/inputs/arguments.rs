//! Parse `fensu dupes` command-line arguments.

use crate::dupes::constants::{DEFAULT_MIN_SIMILARITY, DEFAULT_MIN_TOKENS, DEFAULT_TOP, LANGUAGES};
use crate::dupes::models::DupesOptions;

const USAGE: &str = "usage: fensu dupes [-h] [--json] [--top TOP] [--min-similarity MIN_SIMILARITY]\n                   [--min-tokens MIN_TOKENS] [--lang LANG] [--path PATH]\n                   [--include-tests] [--since REV] [--diff]";
const MIN_SIMILARITY_EXCLUSIVE: f64 = 0.0;
const MAX_SIMILARITY: f64 = 1.0;
const MIN_COUNT: usize = 1;
const VALUE_OPTIONS: &[&str] = &[
    "--top",
    "--min-similarity",
    "--min-tokens",
    "--lang",
    "--path",
    "--since",
];

/// Return parsed options, or `None` when help was requested.
pub(crate) fn parse_arguments(arguments: &[String]) -> Result<Option<DupesOptions>, String> {
    let mut options = DupesOptions {
        json: false,
        top: DEFAULT_TOP,
        min_similarity: DEFAULT_MIN_SIMILARITY,
        min_tokens: DEFAULT_MIN_TOKENS,
        languages: Vec::new(),
        path_globs: Vec::new(),
        include_tests: false,
        since: None,
        diff: false,
    };
    let mut position = 0;
    while position < arguments.len() {
        let argument = arguments[position].as_str();
        let (name, inline) = argument
            .split_once('=')
            .map_or((argument, None), |(name, value)| (name, Some(value)));
        if !VALUE_OPTIONS.contains(&name) {
            if inline.is_some() {
                return Err(usage_error(&format!("unrecognized arguments: {argument}")));
            }
            match name {
                "-h" | "--help" => return Ok(None),
                "--json" => options.json = true,
                "--include-tests" => options.include_tests = true,
                "--diff" => options.diff = true,
                _ => return Err(usage_error(&format!("unrecognized arguments: {argument}"))),
            }
            position += 1;
            continue;
        }
        let value = match inline {
            Some(value) => value,
            None => {
                position += 1;
                arguments.get(position).map(String::as_str).ok_or_else(|| {
                    usage_error(&format!("argument {name}: expected one argument"))
                })?
            }
        };
        options = apply_value(options, name, value)?;
        position += 1;
    }
    if options.languages.is_empty() {
        options.languages = LANGUAGES.to_vec();
    }
    Ok(Some(options))
}

fn apply_value(mut options: DupesOptions, name: &str, value: &str) -> Result<DupesOptions, String> {
    match name {
        "--top" => options.top = positive(name, value)?,
        "--min-tokens" => options.min_tokens = positive(name, value)?,
        "--min-similarity" => {
            let parsed: f64 = value.parse().map_err(|_| {
                usage_error(&format!("argument {name}: invalid float value: '{value}'"))
            })?;
            if !(parsed > MIN_SIMILARITY_EXCLUSIVE && parsed <= MAX_SIMILARITY) {
                return Err(usage_error(&format!("argument {name}: must be in (0, 1]")));
            }
            options.min_similarity = parsed;
        }
        "--lang" => {
            let language = LANGUAGES
                .iter()
                .find(|language| **language == value)
                .ok_or_else(|| {
                    usage_error(&format!(
                        "argument --lang: invalid choice: '{value}' (choose from {})",
                        LANGUAGES.join(", ")
                    ))
                })?;
            if !options.languages.contains(language) {
                options.languages.push(language);
            }
        }
        "--path" => options.path_globs.push(value.to_owned()),
        _ => {
            if value.is_empty() || value.starts_with('-') {
                return Err(usage_error("argument --since: expected a revision"));
            }
            options.since = Some(value.to_owned());
        }
    }
    Ok(options)
}

fn positive(name: &str, value: &str) -> Result<usize, String> {
    match value.parse::<usize>() {
        Ok(parsed) if parsed >= MIN_COUNT => Ok(parsed),
        _ => Err(usage_error(&format!(
            "argument {name}: must be an integer of at least {MIN_COUNT}"
        ))),
    }
}

fn usage_error(message: &str) -> String {
    format!("{USAGE}\nfensu dupes: error: {message}")
}
