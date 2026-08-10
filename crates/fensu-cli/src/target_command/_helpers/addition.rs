use std::path::Path;
use std::time::Duration;

use crate::analyzer::AnalyzerId;
use crate::configuration::main::render_target_config::render_target_config;
use crate::configuration::main::validate_document::validate_document;
use crate::models::{DetectedTarget, TestLayout};
use crate::repository_io::main::acquire_operation_lock::acquire_operation_lock;
use crate::repository_io::main::open_repository::open_repository;
use crate::repository_io::main::read_optional::read_optional;
use crate::repository_io::main::write_if_unchanged::write_if_unchanged;
use crate::repository_io::models::WriteRequest;
use crate::target_command::_helpers::paths::validate_target_path;
use crate::target_command::constants::{
    CONFIG_FILE, OPERATION_LOCK, TEST_PAUSE_ENVIRONMENT, TEST_READY_LOCK,
};
use crate::target_command::models::AddRequest;

pub(crate) fn add_target(repository: &Path, request: &AddRequest) -> Result<(), String> {
    let directory = open_repository(repository)?;
    let _operation_lock = acquire_operation_lock(&directory, OPERATION_LOCK)?;
    let snapshot = read_optional(&directory, Path::new(CONFIG_FILE))?
        .ok_or_else(|| "fensu target add requires existing fensu.toml.".to_owned())?;
    validate_target_path(repository, &request.path)?;
    let original = String::from_utf8(snapshot.content.clone())
        .map_err(|error| format!("fensu.toml is not UTF-8: {error}"))?;
    validate_document(&original, false)?;
    validate_target_name(&original, &request.name)?;
    let target = DetectedTarget {
        name: request.name.clone(),
        analyzer: AnalyzerId::Svelte,
        root: request.path.clone(),
        roots: vec!["src".to_owned()],
        tests: Vec::new(),
        tooling: Vec::new(),
        test_layout: TestLayout::Mirrored,
        framework: Some("sveltekit".to_owned()),
        rule_packs: Vec::new(),
        select: vec!["FW".to_owned()],
    };
    let mut candidate = original;
    if !candidate.ends_with('\n') {
        candidate.push('\n');
    }
    candidate.push('\n');
    candidate.push_str(&render_target_config(&[target])?);
    validate_document(&candidate, false)?;
    pause_for_deterministic_test(&directory)?;
    write_if_unchanged(WriteRequest {
        repository: &directory,
        path: Path::new(CONFIG_FILE),
        expected: Some(&snapshot),
        content: candidate.as_bytes(),
        temporary_prefix: "fensu-target-add",
    })
}

fn validate_target_name(original: &str, name: &str) -> Result<(), String> {
    let document = toml::from_slice::<toml::Value>(original.as_bytes())
        .map_err(|error| format!("Configuration is not valid TOML: {error}"))?;
    let table = document
        .as_table()
        .ok_or_else(|| "Configuration did not contain a TOML table.".to_owned())?;
    let targets = table
        .get("targets")
        .and_then(toml::Value::as_table)
        .ok_or_else(|| {
            "Refusing to convert a legacy or ambiguous configuration; target add requires existing explicit [targets.<name>] blocks."
                .to_owned()
        })?;
    if targets.contains_key(name) {
        return Err(format!("Target {name:?} already exists; no changes made."));
    }
    Ok(())
}

fn pause_for_deterministic_test(repository: &cap_std::fs::Dir) -> Result<(), String> {
    let Ok(raw) = std::env::var(TEST_PAUSE_ENVIRONMENT) else {
        return Ok(());
    };
    let milliseconds = raw
        .parse::<u64>()
        .map_err(|error| format!("Invalid target-add test pause: {error}"))?;
    let _ready = acquire_operation_lock(repository, TEST_READY_LOCK)?;
    std::thread::sleep(Duration::from_millis(milliseconds));
    Ok(())
}
