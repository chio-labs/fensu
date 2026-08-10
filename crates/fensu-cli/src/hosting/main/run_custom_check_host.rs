//! Run the Python custom-check host and return its exit code.

use std::process::Command;

use crate::constants::CUSTOM_CHECK_TARGETS_ENVIRONMENT_VARIABLE;
use crate::hosting::_helpers::authoring::verify_authoring_version;
use crate::hosting::_helpers::interpreter::{exit_code, python_executable};
use crate::models::CliOutput;

pub(crate) fn run_custom_check_host(
    arguments: &[String],
    targets: &[String],
) -> Result<CliOutput, String> {
    verify_authoring_version()?;
    let mut command = Command::new(python_executable()?);
    command
        .args([
            "-c",
            "import sys; from fensu.cli.main.custom_check_host import run_custom_check; raise SystemExit(run_custom_check(argv=tuple(sys.argv[1:])))",
        ])
        .args(arguments)
        .env("PYTHONDONTWRITEBYTECODE", "1");
    if !targets.is_empty() {
        command.env(
            CUSTOM_CHECK_TARGETS_ENVIRONMENT_VARIABLE,
            serde_json::to_string(targets).map_err(|error| error.to_string())?,
        );
    }
    let output = command
        .output()
        .map_err(|error| format!("Could not launch Fensu's custom-check host: {error}"))?;
    Ok(CliOutput {
        stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
        stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
        exit_code: exit_code(output.status),
    })
}
