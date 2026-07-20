use std::fs;
use std::path::Path;
use std::process::{Command, Output};

pub(crate) fn run(repository: &Path, arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_fensu"))
        .arg("memory")
        .args(arguments)
        .current_dir(repository)
        .env("FENSU_PYTHON", repository.join("python-does-not-exist"))
        .env("NO_COLOR", "1")
        .output()
        .expect("native fensu process runs")
}

pub(crate) fn write(path: impl AsRef<Path>, contents: &str) {
    let path = path.as_ref();
    fs::create_dir_all(path.parent().expect("fixture parent")).expect("fixture directory");
    fs::write(path, contents).expect("fixture file");
}

pub(crate) fn assert_success(output: &Output, expected: &str) {
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        String::from_utf8_lossy(&output.stdout).contains(expected),
        "stdout: {}",
        String::from_utf8_lossy(&output.stdout)
    );
}
