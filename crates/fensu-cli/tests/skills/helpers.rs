use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use serde_json::Value;
use sha2::{Digest, Sha256};

pub(crate) const CONFIG: &str = "roots = [\"src/pkg\"]\ntests = []\nselect = [\"FF\"]\n[experimental]\nmemory = true\n[skills]\nname = \"Fixture\"\n";
#[cfg(not(windows))]
const WORKSPACE_PYTHON: &str = ".venv/bin/python";
#[cfg(windows)]
const WORKSPACE_PYTHON: &str = ".venv/Scripts/python.exe";

pub(crate) fn write(path: impl AsRef<Path>, content: impl AsRef<[u8]>) {
    let path = path.as_ref();
    fs::create_dir_all(path.parent().expect("fixture parent")).expect("fixture directory");
    fs::write(path, content).expect("fixture file");
}

pub(crate) fn project() -> tempfile::TempDir {
    let repository = tempfile::tempdir().expect("temporary repository");
    write(repository.path().join("fensu.toml"), CONFIG);
    write(repository.path().join("src/pkg/__init__.py"), b"");
    repository
}

pub(crate) fn native(root: &Path, arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_fensu"))
        .arg("skills")
        .args(arguments)
        .current_dir(root)
        .env("FENSU_PYTHON", root.join("python-does-not-exist"))
        .output()
        .expect("native skills process")
}

pub(crate) fn native_with_python(root: &Path, arguments: &[&str], python: &Path) -> Output {
    Command::new(env!("CARGO_BIN_EXE_fensu"))
        .arg("skills")
        .args(arguments)
        .current_dir(root)
        .env("FENSU_PYTHON", python)
        .output()
        .expect("native custom-rule skills process")
}

pub(crate) fn text(bytes: &[u8]) -> String {
    String::from_utf8(bytes.to_vec()).expect("UTF-8 process output")
}

pub(crate) fn target(root: &Path, agent: &str, identity: &str) -> PathBuf {
    root.join(agent)
        .join("skills")
        .join(identity)
        .join("SKILL.md")
}

pub(crate) fn workspace_python() -> Option<PathBuf> {
    let workspace = Path::new(env!("CARGO_MANIFEST_DIR")).parent()?.parent()?;
    let executable = workspace.join(WORKSPACE_PYTHON);
    executable.is_file().then_some(executable)
}

pub(crate) fn remove_skill(_root: &Path, path: &Path, _original: &[u8]) {
    fs::remove_file(path).expect("remove installed skill");
}

pub(crate) fn stale_skill(root: &Path, _path: &Path, _original: &[u8]) {
    let config = CONFIG.replace("memory = true", "memory = false");
    write(root.join("fensu.toml"), config);
}

pub(crate) fn diverge_skill(_root: &Path, path: &Path, original: &[u8]) {
    write(path, [original, b"manual\n"].concat());
}

pub(crate) fn malform_skill(_root: &Path, path: &Path, original: &[u8]) {
    write(
        path,
        text(original).replace("\"schema\":2", "\"schema\":999"),
    );
}

pub(crate) fn collide_skill(_root: &Path, path: &Path, _original: &[u8]) {
    write(path, b"user guidance\n");
}

pub(crate) fn make_legacy_owned_skill(path: &Path) {
    let content = fs::read_to_string(path).expect("generated skill text");
    let marker = content
        .lines()
        .find(|line| line.starts_with("<!-- fensu-skill-owner: "))
        .expect("ownership marker");
    let raw = marker
        .strip_prefix("<!-- fensu-skill-owner: ")
        .and_then(|value| value.strip_suffix(" -->"))
        .expect("ownership payload");
    let mut ownership: Value = serde_json::from_str(raw).expect("ownership JSON");
    ownership["schema"] = Value::from(1);
    ownership["owner"] = Value::from("legacy-owner-from-another-checkout");
    ownership["input_fingerprint"] = Value::from("legacy-input-from-another-checkout");
    ownership["content_fingerprint"] = Value::from("");
    let provisional_marker = format!(
        "<!-- fensu-skill-owner: {} -->",
        serde_json::to_string(&ownership).expect("provisional ownership JSON")
    );
    let provisional = content.replacen(marker, &provisional_marker, 1);
    ownership["content_fingerprint"] =
        Value::from(format!("{:x}", Sha256::digest(provisional.as_bytes())));
    let final_marker = format!(
        "<!-- fensu-skill-owner: {} -->",
        serde_json::to_string(&ownership).expect("final ownership JSON")
    );
    write(
        path,
        provisional.replacen(&provisional_marker, &final_marker, 1),
    );
}
