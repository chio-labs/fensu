use std::process::Command;

use crate::helpers::{run_check, run_check_with, write};
use crate::test_types::{CheckPolicyTestCase, InvalidCheckConfigTestCase, RuleRemediationTestCase};

const CONFIG: &str =
    "roots = [\"src\"]\ntests = [\"tests\"]\ntooling = [\"scripts\"]\nselect = [\"FFA\"]\n";

#[test]
fn given_path_scoped_rule_ignore_when_checking_then_only_matching_reported_paths_are_filtered() {
    let test_cases = [CheckPolicyTestCase {
        description: "a rule ignore requires both selector and reported path to match",
        expected_exit_code: 1,
        expected_present: "src/pkg/live/bad.py",
        expected_absent: "src/pkg/generated/bad.py",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\n\n[[rule_ignores]]\nrules = [\"FFA\"]\npaths = [\"src/pkg/generated/**\"]\nreason = \"Generated interfaces are checked upstream.\"\n",
        );
        write(
            repository.path().join("src/pkg/generated/bad.py"),
            "def generated(value):\n    return value\n",
        );
        write(
            repository.path().join("src/pkg/live/bad.py"),
            "def live(value):\n    return value\n",
        );

        let output = run_check(repository.path());
        let stdout = String::from_utf8(output.stdout).expect("check stdout is UTF-8");

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(stdout.contains("FFA001"), "{}", test_case.description);
        assert!(
            stdout.contains(test_case.expected_present),
            "{}",
            test_case.description
        );
        assert!(
            !stdout.contains(test_case.expected_absent),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_braced_rule_ignore_pattern_when_checking_then_braces_are_matched_literally() {
    let test_cases = [CheckPolicyTestCase {
        description: "brace characters are literals in native path patterns",
        expected_exit_code: 1,
        expected_present: "src/pkg/generated.py",
        expected_absent: "src/pkg/{generated,vendored}.py",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\n\n[[rule_ignores]]\nrules = [\"FFA001\"]\npaths = [\"src/pkg/{generated,vendored}.py\"]\nreason = \"Literal generated filename.\"\n",
        );
        write(
            repository.path().join("src/pkg/{generated,vendored}.py"),
            "def literal(value):\n    return value\n",
        );
        write(
            repository.path().join("src/pkg/generated.py"),
            "def generated(value):\n    return value\n",
        );

        let output = run_check(repository.path());
        let stdout = String::from_utf8(output.stdout).expect("check stdout is UTF-8");

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_present),
            "{}",
            test_case.description
        );
        assert!(
            !stdout.contains(test_case.expected_absent),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_warning_and_exact_exception_when_rule_ignore_overlaps_then_policy_order_is_preserved() {
    let test_cases = [CheckPolicyTestCase {
        description: "exact exceptions remain visible before overlapping ignores filter findings",
        expected_exit_code: 0,
        expected_present: "Applied 1 rule exception",
        expected_absent: "src/pkg/generated/bad.py:1",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = []\nwarn = [\"FFA001\"]\n\n[[rule_exceptions]]\nrule = \"FFA001\"\npath = \"src/pkg/generated/bad.py\"\nreason = \"Exact accepted adapter.\"\n\n[[rule_ignores]]\nrules = [\"FFA001\"]\npaths = [\"src/pkg/generated/**\"]\nreason = \"Generated interfaces are checked upstream.\"\n",
        );
        write(
            repository.path().join("src/pkg/generated/bad.py"),
            "def generated(value):\n    return value\n",
        );

        let output = run_check_with(repository.path(), &["--warn", "--no-cache"]);
        let stdout = String::from_utf8(output.stdout).expect("check stdout is UTF-8");

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_present),
            "{}",
            test_case.description
        );
        assert!(
            !stdout.contains(test_case.expected_absent),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_malformed_rule_ignore_when_checking_natively_then_configuration_fails_loudly() {
    let test_cases = [InvalidCheckConfigTestCase {
        description: "empty rule ignore selectors are rejected",
        expected_exit_code: 2,
        expected_error: "selectors must not be empty",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "roots = [\"src/pkg\"]\n\n[[rule_ignores]]\nrules = []\npaths = [\"src/**\"]\nreason = \"Required.\"\n",
        );
        write(
            repository.path().join("src/pkg/module.py"),
            "value: int = 1\n",
        );

        let output = run_check(repository.path());

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_error),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_composable_custom_rule_policies_when_inspecting_rules_then_remediations_explain_wrapper() {
    let repository = tempfile::tempdir().expect("temporary repository");
    write(repository.path().join("fensu.toml"), CONFIG);
    let test_cases = [
        RuleRemediationTestCase {
            description: "FFR707 recommends converting wrappers inside the test",
            code: "FFR707",
            expected_fragment: "convert it to RuleCase inside the test",
        },
        RuleRemediationTestCase {
            description: "FFT204 recommends local wrapper dataclasses",
            code: "FFT204",
            expected_fragment: "local wrapper dataclass",
        },
        RuleRemediationTestCase {
            description: "FFT413 recommends constructing framework objects inside tests",
            code: "FFT413",
            expected_fragment: "construct the framework object inside the test",
        },
    ];

    for test_case in &test_cases {
        let output = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["rule", test_case.code, "--color", "never"])
            .current_dir(repository.path())
            .env(
                "FENSU_PYTHON",
                repository.path().join("python-does-not-exist"),
            )
            .output()
            .expect("native rule process runs");

        assert_eq!(output.status.code(), Some(0), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&output.stdout).contains(test_case.expected_fragment),
            "{}",
            test_case.description
        );
    }
}
