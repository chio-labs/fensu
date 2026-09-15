use std::fs;
use std::path::{Path, PathBuf};

pub(crate) const REPOSITORY_RULE_SOURCE: &str = r#"from fensu import AnalyzerId, Family, Fault, ProjectPath, Repository, RuleContext, RuleOption, rule

EXPECTED = RuleOption.string(name="expected", default="v2")
UNUSED = RuleOption.integer(name="limit", default=1)

@rule(code="XREP001", family=Family.CUSTOM, slug="contract-version", message="contract versions differ", analyzers=(AnalyzerId.PYTHON, AnalyzerId.TYPESCRIPT), options=(EXPECTED,), cacheable=True)
def contract_version(*, repository: Repository, ctx: RuleContext) -> list[Fault]:
    del repository
    backend = ctx.targets.named("backend")
    frontend = ctx.targets.named("frontend")
    if backend is None or frontend is None:
        return []
    contract = backend.python.file(ProjectPath("backend/contracts.py"))
    client = frontend.web.file(ProjectPath("frontend/client.ts"))
    if contract is None or client is None or backend.tree.position(contract.file.path) is None or frontend.graph.node(client.file) is None:
        return []
    if "v1" not in contract.source or ctx.option(EXPECTED) not in client.source:
        return []
    return [ctx.path_fault(path=frontend.repository_path(client.file))]

@rule(code="XREP009", family=Family.CUSTOM, slug="unselected-default", message="unselected default", analyzers=(AnalyzerId.PYTHON,), options=(UNUSED,), cacheable=True)
def unselected_default(*, repository: Repository, ctx: RuleContext) -> list[Fault]:
    del repository, ctx
    return []
"#;
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
        .env("FENSU_PYTHON", poison_python(process_directory))
        .env("PATH", process_directory)
        .env("FENSU_PROCESS_MARKER", repository.join("process-invoked"))
        .env("NO_COLOR", "1")
        .output()
        .expect("internal native web check process runs")
}

pub(crate) fn run_web_command(repository: &Path, arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_fensu"))
        .args(arguments)
        .current_dir(repository)
        .env("FENSU_PYTHON", repository.join("python-does-not-exist"))
        .env("NO_COLOR", "1")
        .output()
        .expect("native web command process runs")
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

pub(crate) fn write_repository_rule_fixture(repository: &Path, config: &str) {
    write(
        repository.join("backend/contracts.py"),
        "API_VERSION = 'v1'\n",
    );
    write(
        repository.join("frontend/client.ts"),
        "export const apiVersion = 'v2';\n",
    );
    write(repository.join("rules/custom.py"), REPOSITORY_RULE_SOURCE);
    write(repository.join("fensu.toml"), config);
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
pub(crate) fn workspace_python() -> PathBuf {
    let workspace = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    workspace.join(".venv/bin/python")
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

#[cfg(windows)]
pub(crate) fn workspace_python() -> PathBuf {
    let workspace = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    workspace.join(".venv/Scripts/python.exe")
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
