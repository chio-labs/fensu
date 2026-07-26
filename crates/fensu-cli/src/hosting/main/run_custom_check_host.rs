//! Run the Python custom-check host and return its exit code.

use std::process::Command;

use crate::hosting::_helpers::authoring::verify_authoring_version;
use crate::hosting::_helpers::interpreter::{exit_code, python_executable};

pub(crate) fn run_custom_check_host(arguments: &[String]) -> Result<i32, String> {
    verify_authoring_version()?;
    let status = Command::new(python_executable()?)
        .args([
            "-c",
            "import sys; from fensu.cli.main.custom_check_host import run_custom_check; raise SystemExit(run_custom_check(argv=tuple(sys.argv[1:])))",
        ])
        .args(arguments)
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .status()
        .map_err(|error| format!("Could not launch Fensu's custom-check host: {error}"))?;
    Ok(exit_code(status))
}
