use std::fs;
use std::path::Path;
use std::process::{Command, Output};

pub(crate) fn run_check(repository: &Path) -> Output {
    run_check_with(repository, &["--no-cache"])
}

pub(crate) fn run_check_with(repository: &Path, arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_fensu"))
        .args(["check", "--no-color"])
        .args(arguments)
        .current_dir(repository)
        .env("FENSU_PYTHON", repository.join("python-does-not-exist"))
        .env("NO_COLOR", "1")
        .output()
        .expect("native fensu process runs")
}

pub(crate) fn run_internal_web_check_with(
    repository: &Path,
    arguments: &[&str],
    process_directory: &Path,
) -> Output {
    Command::new(env!("CARGO_BIN_EXE_fensu"))
        .args(["check", "--no-color"])
        .args(arguments)
        .current_dir(repository)
        .env("FENSU_INTERNAL_NATIVE_WEB_ANALYZERS", "1")
        .env("FENSU_PYTHON", poison_python(process_directory))
        .env("PATH", process_directory)
        .env("FENSU_PROCESS_MARKER", repository.join("process-invoked"))
        .env("NO_COLOR", "1")
        .output()
        .expect("internal native web check process runs")
}

pub(crate) fn run_with_internal_web_gate(repository: &Path, arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_fensu"))
        .args(arguments)
        .current_dir(repository)
        .env("FENSU_INTERNAL_NATIVE_WEB_ANALYZERS", "1")
        .env("FENSU_PYTHON", repository.join("python-does-not-exist"))
        .env("NO_COLOR", "1")
        .output()
        .expect("internal-gate command process runs")
}

pub(crate) fn run_check_colored(repository: &Path, arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_fensu"))
        .arg("check")
        .args(arguments)
        .current_dir(repository)
        .env("FENSU_PYTHON", repository.join("python-does-not-exist"))
        .env_remove("NO_COLOR")
        .output()
        .expect("native fensu process runs")
}

pub(crate) fn write(path: impl AsRef<Path>, contents: &str) {
    write_bytes(path, contents.as_bytes());
}

pub(crate) fn write_bytes(path: impl AsRef<Path>, contents: &[u8]) {
    let path = path.as_ref();
    fs::create_dir_all(path.parent().expect("fixture parent")).expect("fixture directory");
    fs::write(path, contents).expect("fixture file");
}

pub(crate) fn create_directory(path: impl AsRef<Path>) {
    fs::create_dir_all(path).expect("fixture directory");
}

#[cfg(unix)]
pub(crate) fn poison_processes(repository: &Path) -> std::path::PathBuf {
    use std::os::unix::fs::PermissionsExt;

    let directory = repository.join("process-bin");
    for name in ["node", "python"] {
        let path = directory.join(name);
        write(&path, "#!/bin/sh\n: > \"$FENSU_PROCESS_MARKER\"\nexit 97\n");
        fs::set_permissions(path, fs::Permissions::from_mode(0o755))
            .expect("poison process is executable");
    }
    directory
}

#[cfg(windows)]
pub(crate) fn poison_processes(repository: &Path) -> std::path::PathBuf {
    let directory = repository.join("process-bin");
    for name in ["node.cmd", "python.cmd"] {
        write(
            directory.join(name),
            "@echo off\r\ntype nul > \"%FENSU_PROCESS_MARKER%\"\r\nexit /b 97\r\n",
        );
    }
    directory
}

#[cfg(unix)]
fn poison_python(process_directory: &Path) -> std::path::PathBuf {
    process_directory.join("python")
}

#[cfg(windows)]
fn poison_python(process_directory: &Path) -> std::path::PathBuf {
    process_directory.join("python.cmd")
}
