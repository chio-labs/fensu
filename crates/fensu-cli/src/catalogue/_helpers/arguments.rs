//! Parse the rule command's arguments and resolve colour use.

use std::env;
use std::io::{self, IsTerminal};

use crate::constants::{COLOR_ALWAYS, COLOR_AUTO, COLOR_NEVER, OPTION_COLOR, OPTION_TARGET};

pub(crate) fn parse_arguments(
    arguments: &[String],
) -> Result<(String, String, Option<String>), String> {
    let mut color = COLOR_AUTO.to_owned();
    let mut code = None;
    let mut target = None;
    let mut index = 0;
    while index < arguments.len() {
        if arguments[index] == OPTION_COLOR {
            index += 1;
            color = arguments.get(index).cloned().ok_or_else(|| {
                "fensu rule: error: argument --color: expected one argument".to_owned()
            })?;
            if !matches!(color.as_str(), COLOR_AUTO | COLOR_ALWAYS | COLOR_NEVER) {
                return Err(format!("fensu rule: error: invalid choice: '{color}'"));
            }
        } else if arguments[index] == OPTION_TARGET {
            index += 1;
            target = Some(
                arguments
                    .get(index)
                    .filter(|value| !value.starts_with('-'))
                    .cloned()
                    .ok_or_else(|| {
                        "fensu rule: error: argument --target: expected one argument".to_owned()
                    })?,
            );
        } else if let Some(value) = arguments[index].strip_prefix("--target=") {
            target = Some(value.to_owned());
        } else if arguments[index].starts_with('-') {
            return Err(format!(
                "fensu rule: error: unrecognized arguments: {}",
                arguments[index]
            ));
        } else {
            code = Some(arguments[index].clone());
        }
        index += 1;
    }
    let code = code.ok_or_else(|| {
        "fensu rule: error: the following arguments are required: code".to_owned()
    })?;
    Ok((color, code, target))
}

pub(crate) fn use_color(color: &str) -> bool {
    env::var_os("NO_COLOR").is_none()
        && (color == COLOR_ALWAYS || color == COLOR_AUTO && io::stdout().is_terminal())
}
