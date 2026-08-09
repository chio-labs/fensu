//! Parse check arguments and resolve colour use.

use std::env;
use std::io::{self, IsTerminal};

use crate::constants::{COLOR_ALWAYS, COLOR_AUTO, COLOR_NEVER, OPTION_TARGET};
use crate::models::CheckOptions;

pub(crate) fn requests_help(arguments: &[String]) -> bool {
    let mut index = 0;
    while index < arguments.len() {
        let argument = arguments[index].as_str();
        if matches!(argument, "--target" | "--color" | "--jobs") {
            index += 2;
            continue;
        }
        if matches!(argument, "--help" | "-h") {
            return true;
        }
        index += 1;
    }
    false
}

pub(crate) fn parse_options(arguments: &[String]) -> Result<CheckOptions, String> {
    let mut options = CheckOptions {
        color: COLOR_AUTO.to_owned(),
        warn: false,
        cache_enabled: None,
        cache_stats: false,
        target: None,
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
            OPTION_TARGET => {
                index += 1;
                let value = arguments
                    .get(index)
                    .filter(|value| !value.starts_with('-'))
                    .ok_or_else(|| "argument --target: expected one argument".to_owned())?;
                options.target = Some(value.clone());
            }
            argument if argument.starts_with("--target=") => {
                options.target = Some(argument[OPTION_TARGET.len() + 1..].to_owned());
            }
            "--jobs" => {
                index += 1;
                let jobs = arguments
                    .get(index)
                    .ok_or_else(|| "argument --jobs: expected one argument".to_owned())?;
                let Ok(jobs) = jobs.parse::<usize>() else {
                    return Err("argument --jobs: jobs must be at least 1".to_owned());
                };
                if jobs == 0 {
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
