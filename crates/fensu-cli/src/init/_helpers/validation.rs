//! Reject initialisation requests the repository state cannot satisfy.

use std::io::{self, IsTerminal};

use crate::init::constants::TESTS_ROOT;
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
    if options.preset.is_some() && !options.excluded_targets.is_empty() {
        return Err("--preset cannot be combined with --exclude-target.".to_owned());
    }
    if (!survey.targets.is_empty() || options.preset.is_some())
        && (!options.roots.is_empty()
            || !options.tests.is_empty()
            || !options.tooling.is_empty()
            || options.name.is_some())
    {
        return Err("Detected or preset targets use explicit target policy; --root, --tests, --tooling, and --name cannot be combined with them.".to_owned());
    }
    for excluded in &options.excluded_targets {
        if !survey.targets.iter().any(|target| &target.name == excluded) {
            return Err(format!(
                "Unknown detected target {excluded:?}. No configuration was written."
            ));
        }
    }
    let all_svelte_excluded = !survey.targets.is_empty()
        && survey
            .targets
            .iter()
            .all(|target| options.excluded_targets.contains(&target.name));
    if all_svelte_excluded
        && !survey
            .package_roots
            .iter()
            .any(|root| root.as_str() != TESTS_ROOT)
    {
        return Err(
            "All detected targets were excluded; no target remains to configure.".to_owned(),
        );
    }
    if survey.empty
        && (!options.roots.is_empty() || !options.tests.is_empty() || !options.tooling.is_empty())
    {
        return Err("--root, --tests, and --tooling options do not apply to an empty repository; use --name NAME.".to_owned());
    }
    if survey.empty && options.yes && options.name.is_none() && options.preset.is_none() {
        return Err("Empty repository initialization with --yes requires --name NAME.\nExample: fensu init --yes --name my_package".to_owned());
    }
    if !options.yes {
        return Err("Interactive initialization is not supported; rerun with --yes.".to_owned());
    }
    Ok(())
}
