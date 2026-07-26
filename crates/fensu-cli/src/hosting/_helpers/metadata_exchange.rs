//! Exchange one request and response with the skills metadata host process.

use std::io::Write;
use std::process::{Child, Command, Stdio};

use crate::hosting::_helpers::interpreter::python_executable;

pub(crate) fn spawn_metadata_host() -> Result<Child, String> {
    Command::new(python_executable()?)
        .args([
            "-c",
            "from fensu.cli.main._skills_metadata_host import main; raise SystemExit(main())",
        ])
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("Could not launch Fensu's custom-rule metadata host: {error}"))
}

pub(crate) fn send_request(mut host: Child, request: &[u8]) -> Result<Child, String> {
    host.stdin
        .take()
        .ok_or_else(|| "Could not open the custom-rule metadata host request stream.".to_owned())?
        .write_all(request)
        .map_err(|error| format!("Could not send custom-rule metadata request: {error}"))?;
    Ok(host)
}

pub(crate) fn read_response(host: Child) -> Result<Vec<u8>, String> {
    let output = host
        .wait_with_output()
        .map_err(|error| format!("Could not read custom-rule metadata response: {error}"))?;
    if !output.status.success() {
        return Err(failure_message(&output.stderr));
    }
    Ok(output.stdout)
}

fn failure_message(stderr: &[u8]) -> String {
    let detail = String::from_utf8_lossy(stderr).trim().to_owned();
    if detail.is_empty() {
        "Fensu's custom-rule metadata host failed without a diagnostic.".to_owned()
    } else {
        format!("Fensu's custom-rule metadata host failed: {detail}")
    }
}
