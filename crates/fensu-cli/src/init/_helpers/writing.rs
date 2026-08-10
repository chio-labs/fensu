//! Write the generated configuration and ignore files.

use std::path::Path;

use crate::configuration::main::render_target_config::render_target_config;
use crate::configuration::main::validate_document::validate_document;
use crate::init::constants::FENSU_IGNORE;
use crate::init::models::InitPlan;
use crate::repository_io::main::open_repository::open_repository;
use crate::repository_io::main::read_optional::read_optional;
use crate::repository_io::main::write_if_unchanged::write_if_unchanged;
use crate::repository_io::models::{SafeFileSnapshot, WriteRequest};

pub(crate) fn write_project_files(
    repository: &Path,
    plan: &InitPlan,
    python_scaffold: bool,
) -> Result<(), String> {
    let directory = open_repository(repository)?;
    let gitignore = read_optional(&directory, Path::new(".gitignore"))?;
    write_config(&directory, plan)?;
    write_gitignore(&directory, gitignore.as_ref(), python_scaffold)
}

fn write_config(repository: &cap_std::fs::Dir, plan: &InitPlan) -> Result<(), String> {
    let text = if plan.targets.is_empty() {
        legacy_config_text(&plan.roots, &plan.tests, &plan.tooling)?
    } else {
        render_target_config(&plan.targets)?
    };
    validate_config_text(&text)?;
    write_if_unchanged(WriteRequest {
        repository,
        path: Path::new("fensu.toml"),
        expected: None,
        content: text.as_bytes(),
        temporary_prefix: "fensu-init-config",
    })
}

fn legacy_config_text(
    roots: &[String],
    tests: &[String],
    tooling: &[String],
) -> Result<String, String> {
    let mut text = format!(
        "roots = {}\ntests = {}\n",
        serde_json::to_string(roots).map_err(|error| error.to_string())?,
        serde_json::to_string(tests).map_err(|error| error.to_string())?
    );
    if !tooling.is_empty() {
        text.push_str(&format!(
            "tooling = {}\n",
            serde_json::to_string(tooling).map_err(|error| error.to_string())?
        ));
    }
    text.push_str("select = [\"FF\"]\n");
    Ok(text)
}

fn validate_config_text(text: &str) -> Result<(), String> {
    validate_document(text, false).map_err(|error| {
        format!(
            "{error}\nRefusing to write fensu.toml. Choose the scopes explicitly, for example: \
             fensu init --yes --root src/<package>"
        )
    })
}

fn write_gitignore(
    repository: &cap_std::fs::Dir,
    existing: Option<&SafeFileSnapshot>,
    python_scaffold: bool,
) -> Result<(), String> {
    let mut value = if let Some(existing) = existing {
        existing.content.clone()
    } else if python_scaffold {
        include_bytes!(concat!(env!("OUT_DIR"), "/python.gitignore")).to_vec()
    } else {
        Vec::new()
    };
    if !value.ends_with(b"\n") && !value.is_empty() {
        value.push(b'\n');
    }
    if !String::from_utf8_lossy(&value).contains(".fensu/cache/") {
        value.extend_from_slice(FENSU_IGNORE.as_bytes());
    }
    write_if_unchanged(WriteRequest {
        repository,
        path: Path::new(".gitignore"),
        expected: existing,
        content: &value,
        temporary_prefix: "fensu-init-ignore",
    })
}
