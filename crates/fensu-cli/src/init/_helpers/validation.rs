//! Reject initialisation requests the repository state cannot satisfy.

use std::io::{self, IsTerminal};

use crate::init::models::RepositorySurvey;
use crate::models::InitOptions;

pub(crate) fn validate_request(
    options: &InitOptions,
    survey: &RepositorySurvey,
) -> Result<(), String> {
    if !options.yes && !io::stdin().is_terminal() {
        return Err(
            "Interactive initialization requires a TTY; use --yes or explicit options.".to_owned(),
        );
    }
    if survey.empty
        && (!options.roots.is_empty() || !options.tests.is_empty() || !options.tooling.is_empty())
    {
        return Err("--root, --tests, and --tooling options do not apply to an empty repository; use --name NAME.".to_owned());
    }
    if survey.empty && options.yes && options.name.is_none() {
        return Err("Empty repository initialization with --yes requires --name NAME.\nExample: fensu init --yes --name my_package".to_owned());
    }
    if !options.yes {
        return Err("Interactive initialization is not supported; rerun with --yes.".to_owned());
    }
    Ok(())
}
