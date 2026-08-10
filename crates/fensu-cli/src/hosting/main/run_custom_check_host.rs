//! Run the versioned Python custom-check host protocol.

use std::process::Command;

use crate::check::models::HostedCheckResponse;
use crate::constants::{CUSTOM_CHECK_PROTOCOL_VERSION, CUSTOM_CHECK_TARGETS_ENVIRONMENT_VARIABLE};
use crate::hosting::_helpers::authoring::verify_authoring_version;
use crate::hosting::_helpers::interpreter::python_executable;

pub(crate) fn run_custom_check_host(
    arguments: &[String],
    targets: &[String],
) -> Result<HostedCheckResponse, String> {
    verify_authoring_version()?;
    let mut command = Command::new(python_executable()?);
    command
        .args([
            "-c",
            "import sys; from fensu.cli.main.custom_check_host import _run_custom_check_protocol; raise SystemExit(_run_custom_check_protocol(argv=tuple(sys.argv[1:])))",
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
    if !output.status.success() {
        let detail = String::from_utf8_lossy(&output.stderr).trim().to_owned();
        return Err(if detail.is_empty() {
            "Fensu's custom-check host failed without a diagnostic.".to_owned()
        } else {
            format!("Fensu's custom-check host failed: {detail}")
        });
    }
    let mut response: HostedCheckResponse = serde_json::from_slice(&output.stdout)
        .map_err(|error| format!("Invalid custom-check host response: {error}"))?;
    if response.protocol != CUSTOM_CHECK_PROTOCOL_VERSION {
        return Err(format!(
            "Incompatible custom-check protocol {}; expected {}.",
            response.protocol, CUSTOM_CHECK_PROTOCOL_VERSION
        ));
    }
    if response.package_version != env!("CARGO_PKG_VERSION") {
        return Err(format!(
            "Custom-check host version {} does not match native fensu {}.",
            response.package_version,
            env!("CARGO_PKG_VERSION")
        ));
    }
    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_owned();
    if !stderr.is_empty() {
        response.messages.push(stderr);
    }
    Ok(response)
}
