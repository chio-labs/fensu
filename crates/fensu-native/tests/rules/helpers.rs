//! Native core-rule contract fixture helpers.

use std::collections::HashMap;
use std::fs;
use std::path::Path;

use fensu_facts::extension::models::ProgramHandle;
use fensu_native::rules::main::evaluate_core_rules::evaluate_core_rules;
use fensu_native::rules::models::{NativeProjectModule, NativeProjectPlane, NativeRuleContext};
use ruff_python_ast::PythonVersion;

use crate::test_types::{CoreRuleFixture, ExpectedFault};

pub(crate) fn run_fixtures(fixtures: Vec<CoreRuleFixture>) {
    for fixture in fixtures {
        let actual = evaluate_fixture(&fixture);
        assert_eq!(actual, fixture.expected_faults, "{}", fixture.description);
    }
}

pub(crate) fn fixtures() -> Vec<CoreRuleFixture> {
    include_str!("fixtures/core_rules.jsonl")
        .lines()
        .map(|line| serde_json::from_str(line).expect("core rule fixture is valid"))
        .collect()
}

fn evaluate_fixture(test_case: &CoreRuleFixture) -> Vec<ExpectedFault> {
    let repository = tempfile::tempdir().expect("fixture repository is creatable");
    materialize_repository(repository.path(), test_case);
    let version = PythonVersion {
        major: 3,
        minor: 12,
    };
    let program = parse_program(&test_case.source, version, &test_case.description);
    let project_sources = test_case
        .project_files
        .iter()
        .map(|file| file.source.clone())
        .collect();
    let project_programs = ProgramHandle::parse_many(project_sources, version);
    let modules = test_case
        .project_files
        .iter()
        .zip(project_programs)
        .filter_map(|(file, program)| {
            program.map(|program| {
                NativeProjectModule::new(
                    file.path.clone(),
                    file.scope.clone(),
                    file.module_parts.clone(),
                    program,
                )
            })
        })
        .collect();
    let project = NativeProjectPlane::new(modules, test_case.entrypoint_modules.clone());
    let repo_root = repository.path().to_string_lossy().replace('\\', "/");
    let context = NativeRuleContext {
        scope: test_case.context.scope.clone(),
        role: test_case.context.role.clone(),
        is_main_module: test_case.context.is_main_module,
        thresholds: test_case.context.thresholds.clone(),
        repository_path: test_case.context.repository_path.clone(),
        contracts: test_case.context.contracts.clone(),
        relative_parts: test_case.context.relative_parts.clone(),
        is_entry_module: test_case.context.is_entry_module,
        package_name: test_case.context.package_name.clone(),
        tooling_packages: test_case.context.tooling_packages.clone(),
        scope_roots: test_case.context.scope_roots.clone(),
        observations: rewritten_observations(&test_case.context.observations, &repo_root),
        custom_registrations: test_case
            .context
            .custom_registrations
            .iter()
            .map(|registration| {
                (
                    registration.0.clone(),
                    registration.1.clone(),
                    registration.2.clone(),
                    registration.3.replace("<repo-root>", &repo_root),
                    registration.4,
                    registration.5,
                )
            })
            .collect(),
        repo_root,
    };

    evaluate_core_rules(&program, &test_case.codes, &context, &project)
        .expect(&test_case.description)
        .into_iter()
        .map(ExpectedFault::from)
        .collect()
}

fn materialize_repository(root: &Path, test_case: &CoreRuleFixture) {
    for entry in &test_case.filesystem {
        let path = root.join(&entry.path);
        entry
            .content
            .as_ref()
            .map_or_else(
                || fs::create_dir_all(&path),
                |content| {
                    fs::create_dir_all(path.parent().expect("fixture file has a parent"))
                        .and_then(|()| fs::write(&path, content))
                },
            )
            .expect("fixture entry is materialized");
    }
}

fn rewritten_observations(
    observations: &HashMap<String, Vec<String>>,
    repo_root: &str,
) -> HashMap<String, Vec<String>> {
    observations
        .iter()
        .map(|(key, values)| {
            (
                key.replace("<repo-root>", repo_root),
                values
                    .iter()
                    .map(|value| value.replace("<repo-root>", repo_root))
                    .collect(),
            )
        })
        .collect()
}

fn parse_program(source: &str, version: PythonVersion, description: &str) -> ProgramHandle {
    ProgramHandle::parse_many(vec![source.to_owned()], version)
        .pop()
        .flatten()
        .unwrap_or_else(|| panic!("fixture source parses: {description}"))
}
