//! Parse check arguments and resolve colour use.

use std::env;
use std::io::{self, IsTerminal};

use crate::constants::{COLOR_ALWAYS, COLOR_AUTO, COLOR_NEVER};
use crate::models::CheckOptions;

pub(crate) fn requests_help(arguments: &[String]) -> bool {
    arguments
        .iter()
        .any(|argument| matches!(argument.as_str(), "--help" | "-h"))
}

pub(crate) fn parse_options(arguments: &[String]) -> Result<CheckOptions, String> {
    let mut options = CheckOptions {
        color: COLOR_AUTO.to_owned(),
        warn: false,
        cache_enabled: None,
        cache_stats: false,
        paths: Vec::new(),
    };
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--no-color" => options.color = COLOR_NEVER.to_owned(),
            "--color" => {
                index += 1;
                let value = arguments
                    .get(index)
                    .ok_or_else(|| "argument --color: expected one argument".to_owned())?;
                if !matches!(value.as_str(), COLOR_AUTO | COLOR_ALWAYS | COLOR_NEVER) {
                    return Err(format!(
                        "argument --color: invalid choice: '{value}' (choose from 'auto', 'always', 'never')"
                    ));
                }
                options.color = value.clone();
            }
            "--warn" => options.warn = true,
            "--cache" => options.cache_enabled = Some(true),
            "--no-cache" => options.cache_enabled = Some(false),
            "--cache-stats" => options.cache_stats = true,
            "--jobs" => {
                index += 1;
                let jobs = arguments
                    .get(index)
                    .ok_or_else(|| "argument --jobs: expected one argument".to_owned())?;
                if jobs
                    .parse::<usize>()
                    .ok()
                    .filter(|jobs| *jobs > 0)
                    .is_none()
                {
                    return Err("argument --jobs: jobs must be at least 1".to_owned());
                }
            }
            argument if argument.starts_with('-') => {
                return Err(format!("unrecognized arguments: {argument}"));
            }
            path => options.paths.push(path.to_owned()),
        }
        index += 1;
    }
    Ok(options)
}

pub(crate) fn use_color(mode: &str) -> bool {
    env::var_os("NO_COLOR").is_none()
        && (mode == COLOR_ALWAYS || mode == COLOR_AUTO && io::stdout().is_terminal())
}
