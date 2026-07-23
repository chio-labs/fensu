use crate::command::constants::{LONG_OPTION_PREFIX, MAP_SHORT_HELP, MAP_USAGE, OPTION_TERMINATOR};
use crate::mapping::constants::{MAP_DIRECTION_DOWNSTREAM, MAP_DIRECTION_UPSTREAM};
use crate::mapping::models::{MapDirection, MapOptions, PathMode};

const LONG_OPTIONS: &[&str] = &[
    "--help",
    "--direction",
    "--depth",
    "--root",
    "--paths",
    "--color",
    "--cache",
    "--no-cache",
    "--cache-stats",
];

pub(crate) fn parse(arguments: &[String]) -> Result<Option<MapOptions>, String> {
    let mut symbol = None;
    let mut direction = MapDirection::Downstream;
    let mut depth = 3;
    let mut roots = Vec::new();
    let mut path_mode = PathMode::Relative;
    let mut color = "auto".to_owned();
    let mut cache_enabled = None;
    let mut cache_stats = false;
    let mut position = 0;
    let mut options_ended = false;
    while position < arguments.len() {
        let argument = &arguments[position];
        if !options_ended && argument == OPTION_TERMINATOR {
            options_ended = true;
            position += 1;
            continue;
        }
        if options_ended {
            if symbol.is_none() {
                symbol = Some(argument.clone());
            } else {
                return Err(parser_error(&format!("unrecognized arguments: {argument}")));
            }
            position += 1;
            continue;
        }
        let (name, inline) = argument
            .split_once('=')
            .map_or((argument.as_str(), None), |(name, value)| {
                (name, Some(value))
            });
        let resolved = resolve_option(name)?;
        match resolved {
            "-h" | "--help" => return Ok(None),
            "--direction" => {
                let value = option_value(arguments, &mut position, resolved, inline)?;
                choice(
                    resolved,
                    value,
                    &[MAP_DIRECTION_DOWNSTREAM, MAP_DIRECTION_UPSTREAM],
                )?;
                direction = if value == MAP_DIRECTION_UPSTREAM {
                    MapDirection::Upstream
                } else {
                    MapDirection::Downstream
                };
            }
            "--depth" => {
                let value = option_value(arguments, &mut position, resolved, inline)?;
                let parsed = value.parse::<i64>().map_err(|_| {
                    parser_error(&format!(
                        "argument --depth: invalid _nonnegative_int value: '{value}'"
                    ))
                })?;
                if parsed < 0 {
                    return Err(parser_error(
                        "argument --depth: depth must be zero or greater",
                    ));
                }
                depth =
                    usize::try_from(parsed).map_err(|error| parser_error(&error.to_string()))?;
            }
            "--root" => {
                roots.push(option_value(arguments, &mut position, resolved, inline)?.to_owned())
            }
            "--paths" => {
                let value = option_value(arguments, &mut position, resolved, inline)?;
                choice(
                    resolved,
                    value,
                    &["absolute", "relative", "compact", "none"],
                )?;
                path_mode = match value {
                    "absolute" => PathMode::Absolute,
                    "compact" => PathMode::Compact,
                    "none" => PathMode::None,
                    _ => PathMode::Relative,
                };
            }
            "--color" => {
                let value = option_value(arguments, &mut position, resolved, inline)?;
                choice(resolved, value, &["auto", "always", "never"])?;
                color = value.to_owned();
            }
            "--cache" => {
                if cache_enabled == Some(false) {
                    return Err(parser_error(
                        "argument --cache: not allowed with argument --no-cache",
                    ));
                }
                cache_enabled = Some(true);
            }
            "--no-cache" => {
                if cache_enabled == Some(true) {
                    return Err(parser_error(
                        "argument --no-cache: not allowed with argument --cache",
                    ));
                }
                cache_enabled = Some(false);
            }
            "--cache-stats" => cache_stats = true,
            _ if resolved.starts_with('-') => {
                return Err(parser_error(&format!("unrecognized arguments: {argument}")));
            }
            _ if symbol.is_none() => symbol = Some(argument.clone()),
            _ => return Err(parser_error(&format!("unrecognized arguments: {argument}"))),
        }
        position += 1;
    }
    let symbol =
        symbol.ok_or_else(|| parser_error("the following arguments are required: symbol"))?;
    Ok(Some(MapOptions {
        symbol,
        direction,
        depth,
        roots,
        path_mode,
        color,
        cache_enabled,
        cache_stats,
    }))
}

fn resolve_option(name: &str) -> Result<&str, String> {
    if name == MAP_SHORT_HELP
        || !name.starts_with(LONG_OPTION_PREFIX)
        || LONG_OPTIONS.contains(&name)
    {
        return Ok(name);
    }
    let matches = LONG_OPTIONS
        .iter()
        .copied()
        .filter(|option| option.starts_with(name))
        .collect::<Vec<_>>();
    match matches.as_slice() {
        [resolved] => Ok(resolved),
        [] => Ok(name),
        _ => Err(parser_error(&format!(
            "ambiguous option: {name} could match {}",
            matches.join(", ")
        ))),
    }
}

fn option_value<'a>(
    arguments: &'a [String],
    position: &mut usize,
    name: &str,
    inline: Option<&'a str>,
) -> Result<&'a str, String> {
    if let Some(value) = inline {
        return Ok(value);
    }
    *position += 1;
    arguments
        .get(*position)
        .map(String::as_str)
        .ok_or_else(|| parser_error(&format!("argument {name}: expected one argument")))
}

fn choice(name: &str, value: &str, choices: &[&str]) -> Result<(), String> {
    if choices.contains(&value) {
        Ok(())
    } else {
        Err(parser_error(&format!(
            "argument {name}: invalid choice: '{value}' (choose from {})",
            choices
                .iter()
                .map(|choice| format!("'{choice}'"))
                .collect::<Vec<_>>()
                .join(", ")
        )))
    }
}

fn parser_error(message: &str) -> String {
    format!("{MAP_USAGE}\nfensu map: error: {message}")
}
