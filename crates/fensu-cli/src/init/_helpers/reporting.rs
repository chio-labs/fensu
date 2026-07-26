//! Render the initialisation summary, drift, and skills output.

use std::collections::BTreeSet;
use std::env;
use std::path::Path;

use crate::init::_helpers::discovery::python_count;
use crate::init::_helpers::packages::{implicit_namespace_packages, report};
use crate::init::constants::NEXT_STEPS;
use crate::init::models::InitPlan;
use crate::models::{CliOutput, InitOptions};
use crate::skills::main::execute;
use crate::skills::models::SkillOptions;

pub(crate) fn finish_report(
    repository: &Path,
    options: &InitOptions,
    plan: &InitPlan,
) -> Result<CliOutput, String> {
    let mut output = summary_text(repository, plan);
    output.push_str(&report(&implicit_namespace_packages(
        repository,
        &plan.roots,
    )));
    output.push_str(&drift_text(repository)?);
    if options.skills.unwrap_or(options.yes) {
        let skill_output = execute::execute(repository, &SkillOptions::default(), true)?;
        if skill_output.exit_code != 0 {
            return Ok(CliOutput {
                stdout: output,
                stderr: skill_output.stderr,
                exit_code: skill_output.exit_code,
            });
        }
        output.push('\n');
        output.push_str(&skill_output.stdout);
    }
    output.push_str(NEXT_STEPS);
    Ok(CliOutput::success(output))
}

fn summary_text(repository: &Path, plan: &InitPlan) -> String {
    let Some(name) = plan.project_name.as_ref() else {
        let runtime_count = plan
            .roots
            .iter()
            .map(|root| python_count(&repository.join(root)))
            .sum::<usize>();
        return format!("-> Existing codebase - {runtime_count} Python files\n\n    Enabling the full Fensu ruleset: FF\n    Wrote fensu.toml\n");
    };
    format!("-> Empty repository\n    Created src/{name}/__init__.py\n    Created tests/\n    Wrote fensu.toml\n")
}

fn drift_text(repository: &Path) -> Result<String, String> {
    let drift = native_drift(repository)?;
    if drift.0 == 0 {
        return Ok("\n-> Found 0 faults\n".to_owned());
    }
    Ok(format!(
        "\n-> Measuring current drift\n\n    Found {} {} across {} {} against the starting ruleset.\n",
        drift.0,
        if drift.0 == 1 { "fault" } else { "faults" },
        drift.1,
        if drift.1 == 1 { "file" } else { "files" }
    ))
}

fn native_drift(repository: &Path) -> Result<(usize, usize), String> {
    let invocation = env::current_dir().map_err(|error| error.to_string())?;
    env::set_current_dir(repository).map_err(|error| error.to_string())?;
    let result = crate::check::main::execute_check::execute_check(&[
        "--no-color".to_owned(),
        "--cache".to_owned(),
    ]);
    env::set_current_dir(invocation).map_err(|error| error.to_string())?;
    let stdout = result?.stdout;
    let faults = stdout.matches(" --> ").count();
    let files = stdout
        .lines()
        .filter_map(|line| line.strip_prefix(" --> "))
        .filter_map(|location| location.rsplitn(3, ':').last())
        .collect::<BTreeSet<_>>()
        .len();
    Ok((faults, files))
}
