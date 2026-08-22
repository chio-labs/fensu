//! Parse the intentionally small structure-checker command surface.

use std::ffi;
use std::path;

const HELP: &str = "Usage: fensu-structure-checker [--root PATH] [--config PATH]\n       fensu-structure-checker --help\n       fensu-structure-checker --version";

#[derive(Debug)]
pub(crate) struct CheckerArguments {
    pub root: Option<path::PathBuf>,
    pub config: Option<path::PathBuf>,
    pub display: Option<String>,
}

pub(crate) fn parse_arguments(
    arguments: impl Iterator<Item = ffi::OsString>,
) -> Result<CheckerArguments, String> {
    let mut parsed = CheckerArguments {
        root: None,
        config: None,
        display: None,
    };
    let mut arguments = arguments.skip(1);
    while let Some(argument) = arguments.next() {
        match argument.to_str() {
            Some("--root") => parsed.root = Some(flag_path("--root", arguments.next())?),
            Some("--config") => parsed.config = Some(flag_path("--config", arguments.next())?),
            Some("--help" | "-h") => parsed.display = Some(HELP.to_owned()),
            Some("--version" | "-V") => {
                parsed.display = Some(format!(
                    "fensu-structure-checker {}",
                    env!("CARGO_PKG_VERSION")
                ));
            }
            Some(value) => return Err(format!("unknown argument {value}\n{HELP}")),
            None => return Err(format!("argument is not valid UTF-8\n{HELP}")),
        }
    }
    Ok(parsed)
}

fn flag_path(flag: &str, value: Option<ffi::OsString>) -> Result<path::PathBuf, String> {
    value
        .filter(|value| !value.is_empty())
        .map(path::PathBuf::from)
        .ok_or_else(|| format!("{flag} requires a path\n{HELP}"))
}
