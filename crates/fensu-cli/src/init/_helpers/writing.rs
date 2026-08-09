//! Write the generated configuration and ignore files.

use std::fs;
use std::path::Path;

use crate::configuration::main::validate_document::validate_document;
use crate::init::constants::FENSU_IGNORE;
use crate::init::models::InitPlan;

pub(crate) fn write_project_files(
    repository: &Path,
    plan: &InitPlan,
    empty: bool,
) -> Result<(), String> {
    write_config(repository, &plan.roots, &plan.tests, &plan.tooling)?;
    write_gitignore(repository, empty)
}

fn write_config(
    repository: &Path,
    roots: &[String],
    tests: &[String],
    tooling: &[String],
) -> Result<(), String> {
    let text = config_text(roots, tests, tooling)?;
    validate_config_text(&text)?;
    fs::write(repository.join("fensu.toml"), text).map_err(|error| error.to_string())
}

fn config_text(roots: &[String], tests: &[String], tooling: &[String]) -> Result<String, String> {
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

fn write_gitignore(repository: &Path, empty: bool) -> Result<(), String> {
    let path = repository.join(".gitignore");
    let mut value = if path.is_file() {
        fs::read(&path).map_err(|error| error.to_string())?
    } else if empty {
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
    fs::write(path, value).map_err(|error| error.to_string())
}
