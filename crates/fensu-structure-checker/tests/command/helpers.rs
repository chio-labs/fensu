//! Process and temporary-workspace support for command tests.

use std::fs;
use std::path;
use std::process;
use std::sync::atomic;

use crate::test_types;

static REPO_COUNTER: atomic::AtomicUsize = atomic::AtomicUsize::new(0);

pub(crate) fn run_checker(test_case: &test_types::CommandTestCase) -> process::Output {
    process::Command::new(env!("CARGO_BIN_EXE_fensu-structure-checker"))
        .args(&test_case.arguments)
        .output()
        .expect("structure checker command starts")
}

pub(crate) fn run_configured_checker() -> process::Output {
    let root = write_configured_fixture();
    let output = process::Command::new(env!("CARGO_BIN_EXE_fensu-structure-checker"))
        .arg("--root")
        .arg(&root)
        .arg("--config")
        .arg(root.join("rust-structure-checker.toml"))
        .output()
        .expect("configured structure checker starts");
    fs::remove_dir_all(root).expect("temporary command fixture is removable");
    output
}

fn write_configured_fixture() -> path::PathBuf {
    let index = REPO_COUNTER.fetch_add(1, atomic::Ordering::SeqCst);
    let root = std::env::temp_dir().join(format!(
        "fensu-structure-checker-command-{}-{index}",
        process::id()
    ));
    let source_root = root.join("crates/example/src/rules/_helpers");
    fs::create_dir_all(&source_root).expect("temporary command fixture is writable");
    fs::write(
        root.join("Cargo.toml"),
        "[workspace]\nmembers = [\"crates/example\"]\nresolver = \"2\"\n\n[workspace.package]\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n",
    )
    .expect("temporary workspace manifest is writable");
    fs::write(
        root.join("crates/example/Cargo.toml"),
        "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n",
    )
    .expect("temporary crate manifest is writable");
    fs::write(
        source_root.join("annotations.rs"),
        "use sqlparser::ast::Statement;\n",
    )
    .expect("temporary source is writable");
    fs::write(
        root.join("rust-structure-checker.toml"),
        "schema-version = 1\n\n[tooling]\npackage = \"example-structure-checker\"\nruntime-forbidden-packages = [\"example-structure-checker\", \"fensu-structure-checker\"]\n\n[raw-parser-boundary]\npackages = [\"sqlparser\"]\nremediation = \"consume shared SQL fact rows\"\n",
    )
    .expect("temporary checker config is writable");
    root
}
