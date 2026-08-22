//! Isolated process transport for custom-rule hosts.

use std::io::Write;
use std::path::Path;
use std::process::{Command, Output, Stdio};

use crate::lifecycle::errors::LifecycleError;

pub(crate) fn exchange(
    program: &Path,
    arguments: &[String],
    input: &[u8],
) -> Result<Output, LifecycleError> {
    let mut child = Command::new(program)
        .args(arguments)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(launch_error)?;
    let mut stdin = child
        .stdin
        .take()
        .ok_or_else(|| LifecycleError::HostLaunch {
            message: "custom host stdin was unavailable".to_owned(),
        })?;
    stdin.write_all(input).map_err(launch_error)?;
    stdin.write_all(b"\n").map_err(launch_error)?;
    drop(stdin);
    child.wait_with_output().map_err(launch_error)
}

fn launch_error(error: std::io::Error) -> LifecycleError {
    LifecycleError::HostLaunch {
        message: error.to_string(),
    }
}
