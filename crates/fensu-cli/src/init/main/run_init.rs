//! Initialise a repository for Fensu.

use std::env;

use crate::init::_helpers::arguments::parse_init;
use crate::init::_helpers::discovery::{existing_configuration, local_config, survey_repository};
use crate::init::_helpers::layout::plan_layout;
use crate::init::_helpers::reporting::finish_report;
use crate::init::_helpers::validation::validate_request;
use crate::init::_helpers::writing::write_project_files;
use crate::init::constants::INIT_USAGE;
use crate::models::CliOutput;

pub(crate) fn run_init(arguments: &[String]) -> Result<CliOutput, String> {
    let options = parse_init(arguments)?;
    if options.help {
        return Ok(CliOutput::success(INIT_USAGE.to_owned()));
    }
    let repository = env::current_dir().map_err(|error| error.to_string())?;
    if let Some(path) = local_config(&repository) {
        return existing_configuration(&path, &options);
    }
    let survey = survey_repository(&repository);
    validate_request(&options, &survey)?;
    let plan = plan_layout(&repository, &options, &survey)?;
    write_project_files(&repository, &plan, survey.empty)?;
    finish_report(&repository, &options, &plan)
}
