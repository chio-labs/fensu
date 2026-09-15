use crate::helpers::{
    require_workspace_python, write, write_repository_rule_fixture, REPOSITORY_RULE_SOURCE,
};
use crate::test_types::RepositoryRuleTestCase;

const ACTIVE_CONFIG: &str = r#"[targets.backend]
analyzer = "python"
roots = ["backend"]
tests = []
tooling = []
select = []

[targets.frontend]
analyzer = "typescript"
roots = ["frontend"]
tests = []
tooling = []
select = []

[repository_rules]
rule_paths = ["rules/custom.py"]
select = ["XREP001"]
"#;

#[test]
fn given_cross_target_repository_rule_when_checking_all_targets_then_emits_once() {
    let test_cases = [RepositoryRuleTestCase {
        description: "aggregate repository rule reports once",
        expected_exit_code: 1,
        expected_primary: "frontend/client.ts:-:-",
        expected_secondary: "XREP001",
    }];
    for test_case in test_cases {
        let python = require_workspace_python!();
        let repository = tempfile::tempdir().expect("temporary repository");
        write_repository_rule_fixture(repository.path(), ACTIVE_CONFIG);

        let output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", python)
            .output()
            .expect("repository check runs");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_primary),
            "{}: {stdout}",
            test_case.description
        );
        assert_eq!(
            stdout.matches(test_case.expected_secondary).count(),
            1,
            "{}: {stdout}",
            test_case.description
        );

        let metadata = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["rule", "XREP001", "--color", "never"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", crate::helpers::workspace_python())
            .output()
            .expect("repository rule metadata renders");
        let metadata_stdout = String::from_utf8_lossy(&metadata.stdout);
        let metadata_stderr = String::from_utf8_lossy(&metadata.stderr);
        assert_eq!(
            metadata.status.code(),
            Some(0),
            "{}: {metadata_stdout} {metadata_stderr}",
            test_case.description
        );
        assert!(
            metadata_stdout.contains("Execution owner: repository"),
            "{}: {metadata_stdout}",
            test_case.description
        );
        assert!(
            metadata_stdout.contains("Analyzers: python, typescript"),
            "{}: {metadata_stdout}",
            test_case.description
        );

        let install_root = repository.path().join("installed-skill");
        let install_root_argument = install_root.to_string_lossy().into_owned();
        let skills = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args([
                "skills",
                "--target",
                "agents",
                "--install-root",
                &install_root_argument,
                "--force",
            ])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", crate::helpers::workspace_python())
            .output()
            .expect("repository skills metadata renders");
        let skills_stdout = String::from_utf8_lossy(&skills.stdout);
        let skills_stderr = String::from_utf8_lossy(&skills.stderr);
        assert_eq!(
            skills.status.code(),
            Some(0),
            "{}: {skills_stdout} {skills_stderr}",
            test_case.description
        );
        let skills_directory = install_root.join(".agents/skills");
        let skill_directory = std::fs::read_dir(&skills_directory)
            .expect("skill directory")
            .next()
            .expect("generated skill")
            .expect("generated skill entry")
            .path();
        let skill = std::fs::read_to_string(skill_directory.join("SKILL.md"))
            .expect("generated repository skill");
        assert!(
            skill.contains("## Repository Rules"),
            "{}: {skill}",
            test_case.description
        );
        assert!(
            skill.contains("XREP001: contract-version"),
            "{}: {skill}",
            test_case.description
        );
        assert!(
            skill.contains("ctx.targets.named(name)"),
            "{}: {skill}",
            test_case.description
        );
    }
}

#[test]
fn given_repository_rule_when_checking_one_target_then_skips_without_python() {
    let test_cases = [RepositoryRuleTestCase {
        description: "target-scoped check skips repository rule",
        expected_exit_code: 0,
        expected_primary: "Found 0 faults",
        expected_secondary: "XREP001",
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write_repository_rule_fixture(repository.path(), ACTIVE_CONFIG);

        let output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--target", "frontend", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", repository.path().join("missing-python"))
            .output()
            .expect("target-scoped check runs");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_primary),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            !stdout.contains(test_case.expected_secondary),
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_unselected_repository_rule_when_checking_then_does_not_start_python() {
    let test_cases = [RepositoryRuleTestCase {
        description: "unselected repository rule remains native-only",
        expected_exit_code: 0,
        expected_primary: "Found 0 faults",
        expected_secondary: "",
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write_repository_rule_fixture(
            repository.path(),
            &ACTIVE_CONFIG.replace("select = [\"XREP001\"]", "select = []"),
        );

        let output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", repository.path().join("missing-python"))
            .output()
            .expect("native-only aggregate check runs");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_primary),
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_cacheable_repository_rule_when_registry_changes_then_result_invalidates() {
    let test_cases = [RepositoryRuleTestCase {
        description: "repository cache replays and registry changes invalidate",
        expected_exit_code: 0,
        expected_primary: "Found 0 faults",
        expected_secondary: "Cache: hits=",
    }];
    for test_case in test_cases {
        let python = require_workspace_python!();
        let repository = tempfile::tempdir().expect("temporary repository");
        write_repository_rule_fixture(repository.path(), ACTIVE_CONFIG);

        let first = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--cache", "--cache-stats"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", &python)
            .output()
            .expect("first repository check runs");
        let second = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--cache", "--cache-stats"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", &python)
            .output()
            .expect("cached repository check runs");
        assert_eq!(
            first.stdout, second.stdout,
            "{}: cached output must be byte-identical",
            test_case.description
        );
        assert_eq!(
            second.status.code(),
            Some(1),
            "{}: cached check exit code",
            test_case.description
        );
        let second_stderr = String::from_utf8_lossy(&second.stderr);
        assert!(
            second_stderr.contains(test_case.expected_secondary),
            "{}: {second_stderr}",
            test_case.description
        );

        write(
            repository.path().join("frontend/unused.ts"),
            "export const unrelated = true;\n",
        );
        let unrelated = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--cache", "--cache-stats"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", &python)
            .output()
            .expect("unrelated-edit repository check runs");
        let unrelated_stderr = String::from_utf8_lossy(&unrelated.stderr);
        assert_eq!(
            second.stdout, unrelated.stdout,
            "{}: narrow query output must survive",
            test_case.description
        );
        assert_eq!(
            unrelated.status.code(),
            Some(1),
            "{}: {unrelated_stderr}",
            test_case.description
        );
        assert!(
            unrelated_stderr.contains("hits="),
            "{}: {unrelated_stderr}",
            test_case.description
        );

        write(
            repository
                .path()
                .join(".fensu/cache/repository-custom-v1.json"),
            "{not-json",
        );
        let recovered = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--cache", "--cache-stats"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", &python)
            .output()
            .expect("corrupted repository cache recovers");
        let recovered_stderr = String::from_utf8_lossy(&recovered.stderr);
        assert_eq!(
            unrelated.stdout, recovered.stdout,
            "{}: corruption fallback output must be byte-identical",
            test_case.description
        );
        assert_eq!(
            recovered.status.code(),
            Some(1),
            "{}: {recovered_stderr}",
            test_case.description
        );

        write(
            repository.path().join("fensu.toml"),
            &ACTIVE_CONFIG.replace("[targets.frontend]", "[targets.client]"),
        );
        let renamed = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--cache", "--cache-stats"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", python)
            .output()
            .expect("renamed-registry check runs");
        let stdout = String::from_utf8_lossy(&renamed.stdout);
        let stderr = String::from_utf8_lossy(&renamed.stderr);

        assert_eq!(
            renamed.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_primary),
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_rust_and_svelte_targets_when_repository_rule_queries_facts_then_emits_once() {
    let test_cases = [RepositoryRuleTestCase {
        description: "Rust and Svelte facts compose",
        expected_exit_code: 1,
        expected_primary: "frontend/src/routes/+page.svelte:-:-",
        expected_secondary: "XREP002",
    }];
    for test_case in test_cases {
        let python = require_workspace_python!();
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("backend/Cargo.toml"),
            "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        );
        write(
            repository.path().join("backend/src/lib.rs"),
            "pub fn contract_version() -> usize { 1 }\n",
        );
        write(
            repository.path().join("frontend/src/routes/+page.svelte"),
            "<script lang=\"ts\">const version = 2;</script>\n<p>{version}</p>\n",
        );
        write(
            repository.path().join("frontend/src/lib/value.ts"),
            "export const value: number = 1;\n",
        );
        write(
            repository.path().join("rules/custom.py"),
            r#"from fensu import AnalyzerId, Family, Fault, ProjectPath, Repository, RuleContext, rule

@rule(code="XREP002", family=Family.CUSTOM, slug="native-contract", message="native contracts differ", analyzers=(AnalyzerId.RUST, AnalyzerId.SVELTE), cacheable=True)
def native_contract(*, repository: Repository, ctx: RuleContext) -> list[Fault]:
    del repository
    backend = ctx.targets.named("backend")
    frontend = ctx.targets.named("frontend")
    if backend is None or frontend is None:
        return []
    rust = backend.rust.file(ProjectPath("src/lib.rs"))
    page = frontend.web.file(ProjectPath("src/routes/+page.svelte"))
    support = frontend.web.file(ProjectPath("src/lib/value.ts"))
    if rust is None or page is None or support is None or not rust.items or page.svelte is None or frontend.tree.position(support.file.path) is None:
        return []
    return [ctx.path_fault(path=frontend.repository_path(page.file))]
"#,
        );
        write(
            repository.path().join("fensu.toml"),
            r#"[targets.backend]
analyzer = "rust"
root = "backend"
roots = ["src"]
tests = []
tooling = []
select = []

[targets.frontend]
analyzer = "svelte"
root = "frontend"
roots = ["src"]
tests = []
tooling = []
select = []

[repository_rules]
rule_paths = ["rules/custom.py"]
select = ["XREP002"]
"#,
        );

        let output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", python)
            .output()
            .expect("native repository check runs");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_primary),
            "{}: {stdout}",
            test_case.description
        );
        assert_eq!(
            stdout.matches(test_case.expected_secondary).count(),
            1,
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_repository_options_warnings_and_exceptions_when_checking_then_policy_composes() {
    let test_cases = [RepositoryRuleTestCase {
        description: "repository policy options warnings and exceptions compose",
        expected_exit_code: 0,
        expected_primary: "Applied 1 rule exception",
        expected_secondary: "XREP001",
    }];
    for test_case in test_cases {
        let python = require_workspace_python!();

        let option_repository = tempfile::tempdir().expect("temporary option repository");
        write_repository_rule_fixture(
            option_repository.path(),
            &format!(
                "{ACTIVE_CONFIG}\n[repository_rules.rule_options.XREP001]\nexpected = \"v3\"\n"
            ),
        );
        let option_output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(option_repository.path())
            .env("FENSU_PYTHON", &python)
            .output()
            .expect("repository option check runs");
        let option_stdout = String::from_utf8_lossy(&option_output.stdout);
        let option_stderr = String::from_utf8_lossy(&option_output.stderr);
        assert_eq!(
            option_output.status.code(),
            Some(0),
            "{}: {option_stdout} {option_stderr}",
            test_case.description
        );

        let warning_repository = tempfile::tempdir().expect("temporary warning repository");
        write_repository_rule_fixture(
            warning_repository.path(),
            &ACTIVE_CONFIG.replace("select = [\"XREP001\"]", "warn = [\"XREP001\"]"),
        );
        let warning_output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--warn", "--no-color", "--no-cache"])
            .current_dir(warning_repository.path())
            .env("FENSU_PYTHON", &python)
            .output()
            .expect("repository warning check runs");
        let warning_stdout = String::from_utf8_lossy(&warning_output.stdout);
        let warning_stderr = String::from_utf8_lossy(&warning_output.stderr);
        assert_eq!(
            warning_output.status.code(),
            Some(0),
            "{}: {warning_stdout} {warning_stderr}",
            test_case.description
        );
        assert!(
            warning_stdout.contains(test_case.expected_secondary),
            "{}: {warning_stdout}",
            test_case.description
        );

        let exception_repository = tempfile::tempdir().expect("temporary exception repository");
        write_repository_rule_fixture(
        exception_repository.path(),
        &format!(
            "{ACTIVE_CONFIG}\n[[repository_rules.rule_exceptions]]\nrule = \"XREP001\"\npath = \"frontend/client.ts\"\nreason = \"Accepted compatibility window.\"\n"
        ),
    );
        let exception_output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(exception_repository.path())
            .env("FENSU_PYTHON", python)
            .output()
            .expect("repository exception check runs");
        let exception_stdout = String::from_utf8_lossy(&exception_output.stdout);
        let exception_stderr = String::from_utf8_lossy(&exception_output.stderr);
        assert_eq!(
            exception_output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {exception_stdout} {exception_stderr}",
            test_case.description
        );
        assert!(
            exception_stdout.contains(test_case.expected_primary),
            "{}: {exception_stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_undeclared_target_capability_when_repository_rule_queries_it_then_fails_closed() {
    let test_cases = [RepositoryRuleTestCase {
        description: "undeclared repository capability fails closed",
        expected_exit_code: 2,
        expected_primary: "did not declare typescript target facts",
        expected_secondary: "",
    }];
    for test_case in test_cases {
        let python = require_workspace_python!();
        let repository = tempfile::tempdir().expect("temporary repository");
        write_repository_rule_fixture(repository.path(), ACTIVE_CONFIG);
        write(
            repository.path().join("rules/custom.py"),
            &REPOSITORY_RULE_SOURCE.replace(
                "(AnalyzerId.PYTHON, AnalyzerId.TYPESCRIPT)",
                "(AnalyzerId.PYTHON,)",
            ),
        );

        let output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", python)
            .output()
            .expect("undeclared-capability check runs");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(
            stderr.contains(test_case.expected_primary),
            "{}: {stderr}",
            test_case.description
        );
    }
}
