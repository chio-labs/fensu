use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

pub(crate) const CONFIG: &str = "roots = [\"src/pkg\"]\ntests = []\nselect = [\"FF\"]\n[experimental]\nmemory = true\n[skills]\nname = \"Fixture\"\n";

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
    write(path, text(original).replace("\"schema\":1", "\"schema\":2"));
}

pub(crate) fn collide_skill(_root: &Path, path: &Path, _original: &[u8]) {
    write(path, b"user guidance\n");
}
