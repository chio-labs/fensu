use std::env;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitStatus, Stdio};

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

pub(crate) fn run_skills_metadata_host(request: &[u8]) -> Result<Vec<u8>, String> {
    let mut child = Command::new(python_executable()?)
        .args([
            "-c",
            "from fensu.cli.main._skills_metadata_host import main; raise SystemExit(main())",
        ])
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("Could not launch Fensu's custom-rule metadata host: {error}"))?;
    child
        .stdin
        .take()
        .ok_or_else(|| "Could not open the custom-rule metadata host request stream.".to_owned())?
        .write_all(request)
        .map_err(|error| format!("Could not send custom-rule metadata request: {error}"))?;
    let output = child
        .wait_with_output()
        .map_err(|error| format!("Could not read custom-rule metadata response: {error}"))?;
    if !output.status.success() {
        let detail = String::from_utf8_lossy(&output.stderr).trim().to_owned();
        return Err(if detail.is_empty() {
            "Fensu's custom-rule metadata host failed without a diagnostic.".to_owned()
        } else {
            format!("Fensu's custom-rule metadata host failed: {detail}")
        });
    }
    Ok(output.stdout)
}

fn exit_code(status: ExitStatus) -> i32 {
    status.code().unwrap_or(2)
}
