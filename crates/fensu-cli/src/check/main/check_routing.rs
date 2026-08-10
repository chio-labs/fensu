//! Read help and named target selection before check-host routing.

use crate::check::models::CheckRouting;
use crate::constants::{OPTION_HELP, OPTION_HELP_SHORT, OPTION_TARGET};

pub(crate) fn check_routing(arguments: &[String]) -> Result<CheckRouting<'_>, String> {
    let mut selected: Option<&str> = None;
    let mut help = false;
    let mut index = 0;
    while index < arguments.len() {
        if arguments[index] == OPTION_TARGET {
            index += 1;
            selected = Some(
                arguments
                    .get(index)
                    .filter(|value| !value.starts_with('-'))
                    .ok_or_else(|| "argument --target: expected one argument".to_owned())?,
            );
        } else if let Some(value) = arguments[index].strip_prefix("--target=") {
            selected = Some(value);
        } else if matches!(arguments[index].as_str(), OPTION_HELP | OPTION_HELP_SHORT) {
            help = true;
        }
        index += 1;
    }
    Ok(CheckRouting {
        help,
        target: selected,
    })
}
