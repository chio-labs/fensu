use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use crate::test_types::{CheckTestCase, InitTestCase};

pub(crate) const BASE: &str = "roots = ['src/orders']\ntests = ['tests']\nselect = []\n";
pub(crate) const ENABLED: &str = "[dead_code]\nenabled = true\n";
pub(crate) const ROOT: &str = "[[dead_code.roots]]\nmodules = ['orders.service.main.*']\nsymbols = ['parse_orders']\nreason = 'Handlers are selected by a runtime dispatch table.'\n";

pub(crate) fn run_check_case(test_case: &CheckTestCase, python: Option<&Path>) -> Vec<i32> {
    let workspace = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let root = tempfile::tempdir().expect("fixture repository can be created");
    let python = python
        .map(Path::to_path_buf)
        .unwrap_or_else(|| root.path().join("unavailable-python"));
    let mut statuses: Vec<i32> = Vec::new();
    write(root.path(), "fensu.toml", &test_case.config);
    write(root.path(), "src/orders/__init__.py", "");
    write(
        root.path(),
        "src/orders/service/main/_parse.py",
        "def parse_orders(): pass\n",
    );
    write(
        root.path(),
        "src/orders/service/main/parse.py",
        "def parse_orders(): pass\n",
    );
    write(
        root.path(),
        "tests/test_orders.py",
        "from orders.service.main._parse import parse_orders\ndef test_parse(): parse_orders()\n",
    );
    for step in &test_case.expected_steps {
        for config in step.config.iter() {
            write(root.path(), "fensu.toml", config);
        }
        for (path, source) in step.writes.iter().filter(|(_, source)| source.is_some()) {
            write(
                root.path(),
                path,
                source.expect("write operations include source"),
            );
        }
        for (path, _) in step.writes.iter().filter(|(_, source)| source.is_none()) {
            fs::remove_file(root.path().join(path)).expect("fixture file exists before deletion");
        }
        let output = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color"])
            .env("FENSU_PYTHON", &python)
            .env("PYTHONPATH", workspace.join("src"))
            .current_dir(root.path())
            .output()
            .expect("native CLI process starts");
        let text = format!(
            "{}{}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        );
        statuses.push(output.status.code().expect("check exits normally"));
        for expected in step.contains {
            assert!(text.contains(expected), "{}: {text}", test_case.description);
        }
        for unexpected in step.absent {
            assert!(
                !text.contains(unexpected),
                "{}: {text}",
                test_case.description
            );
        }
    }
    statuses
}

pub(crate) fn run_init_case(test_case: &InitTestCase) -> bool {
    let root = tempfile::tempdir().expect("fixture repository can be created");
    for (path, source) in test_case.files {
        write(root.path(), path, source);
    }
    let output = Command::new(env!("CARGO_BIN_EXE_fensu"))
        .arg("init")
        .args(test_case.arguments)
        .current_dir(root.path())
        .output()
        .expect("native init process starts");
    assert!(
        output.status.success(),
        "{}: {}",
        test_case.description,
        String::from_utf8_lossy(&output.stderr)
    );
    let text =
        fs::read_to_string(root.path().join("fensu.toml")).expect("init wrote configuration");
    let config: toml::Value = toml::from_str(&text).expect("generated configuration is valid TOML");
    let enabled = config
        .get("dead_code")
        .and_then(|value| value.get("enabled"))
        .and_then(toml::Value::as_bool)
        .unwrap_or(false);
    enabled
}

fn write(root: &Path, path: &str, text: &str) {
    let path = root.join(path);
    fs::create_dir_all(path.parent().expect("fixture path has a parent"))
        .expect("fixture directory is writable");
    fs::write(path, text).expect("fixture source is writable");
}

#[cfg(unix)]
pub(crate) fn workspace_python() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.venv/bin/python")
}

#[cfg(windows)]
pub(crate) fn workspace_python() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.venv/Scripts/python.exe")
}

macro_rules! require_workspace_python {
    () => {{
        let python = crate::helpers::workspace_python();
        if !python.is_file() {
            return;
        }
        python
    }};
}
pub(crate) use require_workspace_python;
