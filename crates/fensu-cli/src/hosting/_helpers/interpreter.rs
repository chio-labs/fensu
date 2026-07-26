//! Locate the environment interpreter and read process exit codes.

use std::env;
use std::path::PathBuf;
use std::process::ExitStatus;

pub(crate) fn python_executable() -> Result<PathBuf, String> {
    if let Some(value) = env::var_os("FENSU_PYTHON") {
        return Ok(PathBuf::from(value));
    }
    let current = env::current_exe().map_err(|error| error.to_string())?;
    let directory = current
        .parent()
        .ok_or_else(|| "Could not locate the command environment.".to_owned())?;
    for name in ["python", "python3", "python.exe"] {
        let candidate = directory.join(name);
        if candidate.is_file() {
            return Ok(candidate);
        }
    }
    Err("Could not locate the environment's Python interpreter for this command.".to_owned())
}

pub(crate) fn exit_code(status: ExitStatus) -> i32 {
    status.code().unwrap_or(2)
}
