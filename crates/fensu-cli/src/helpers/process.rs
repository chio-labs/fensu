use std::env;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitStatus};

pub(crate) fn run_python(arguments: &[String]) -> Result<i32, String> {
    verify_authoring_version()?;
    let status = Command::new(python_executable()?)
        .arg("-m")
        .arg("fensu")
        .args(arguments)
        .status()
        .map_err(|error| format!("Could not launch Fensu's Python command host: {error}"))?;
    Ok(exit_code(status))
}

pub(crate) fn verify_authoring_version() -> Result<(), String> {
    let Some(version) = installed_authoring_version() else {
        return Err(
            "fensu is not installed beside fensu-cli; install `fensu` or use the CLI package only for `--version`."
                .to_owned(),
        );
    };
    if version != env!("CARGO_PKG_VERSION") {
        return Err(format!(
            "fensu-cli {} does not match installed fensu {version}. Upgrade both packages together with `python -m pip install --upgrade fensu`. ",
            env!("CARGO_PKG_VERSION")
        ));
    }
    Ok(())
}

fn installed_authoring_version() -> Option<String> {
    let executable = env::current_exe().ok()?;
    let prefix = executable.parent()?.parent()?;
    let candidates = [prefix.join("Lib/site-packages"), prefix.join("lib")];
    for candidate in candidates {
        if candidate.ends_with("lib") {
            let entries = candidate.read_dir().ok()?;
            for entry in entries.flatten() {
                let site = entry.path().join("site-packages");
                if let Some(version) = metadata_version(&site) {
                    return Some(version);
                }
            }
        } else if let Some(version) = metadata_version(&candidate) {
            return Some(version);
        }
    }
    None
}

fn metadata_version(site_packages: &Path) -> Option<String> {
    for entry in site_packages.read_dir().ok()?.flatten() {
        let path = entry.path();
        let name = path.file_name()?.to_str()?;
        if !name.starts_with("fensu-") || !name.ends_with(".dist-info") {
            continue;
        }
        let metadata = std::fs::read_to_string(path.join("METADATA")).ok()?;
        return metadata
            .lines()
            .find_map(|line| line.strip_prefix("Version: ").map(str::to_owned));
    }
    None
}

fn python_executable() -> Result<PathBuf, String> {
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

fn exit_code(status: ExitStatus) -> i32 {
    status.code().unwrap_or(2)
}
