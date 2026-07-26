use std::process::Command;

use crate::helpers::{run_check, run_check_colored, write};
use crate::test_types::{
    CheckPolicyTestCase, ColoredCheckTestCase, InvalidCheckConfigTestCase, RuleColorTestCase,
    RuleOptionsCheckRoutingTestCase, RuleRemediationTestCase,
};

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
fn given_forced_color_when_checking_then_faults_render_in_historical_orange() {
    let test_cases = [ColoredCheckTestCase {
        description: "--color always emits bold orange fault codes without a terminal",
        arguments: &["--color", "always", "--no-cache"],
        expected_exit_code: 1,
        expected_fragment: "\x1b[1;38;5;208mFFA001\x1b[0m",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\n",
        );
        write(
            repository.path().join("src/pkg/bad.py"),
            "def bad(value):\n    return value\n",
        );

        let output = run_check_colored(repository.path(), test_case.arguments);
        let stdout = String::from_utf8(output.stdout).expect("check stdout is UTF-8");

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_fragment),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_forced_color_when_inspecting_rule_then_fault_code_renders_in_orange() {
    let test_cases = [RuleColorTestCase {
        description: "rule lookup uses the same bold orange code as fault output",
        expected_fragment: "\x1b[1;38;5;208mFFA001\x1b[0m parameter-annotation",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        let output = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["rule", "FFA001", "--color", "always"])
            .current_dir(repository.path())
            .output()
            .expect("native rule process runs");
        let stdout = String::from_utf8(output.stdout).expect("rule stdout is UTF-8");

        assert_eq!(output.status.code(), Some(0), "{}", test_case.description);
        assert!(
            stdout.contains(test_case.expected_fragment),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_malformed_rule_ignore_when_checking_natively_then_configuration_fails_loudly() {
    let test_cases = [InvalidCheckConfigTestCase {
        description: "empty rule ignore selectors are rejected",
        config: "roots = [\"src/pkg\"]\n\n[[rule_ignores]]\nrules = []\npaths = [\"src/**\"]\nreason = \"Required.\"\n",
        expected_exit_code: 2,
        expected_error: "selectors must not be empty",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
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
fn given_malformed_rule_options_when_checking_then_native_structure_validation_rejects_them() {
    let test_cases = [
        InvalidCheckConfigTestCase {
            description: "rule options must be a table",
            config: "roots = [\"src/pkg\"]\nrule_options = true\n",
            expected_exit_code: 2,
            expected_error: "Config key rule_options must be a table.",
        },
        InvalidCheckConfigTestCase {
            description: "each rule option entry must be a table",
            config: "roots = [\"src/pkg\"]\n[rule_options]\nXOP001 = true\n",
            expected_exit_code: 2,
            expected_error: "Config key rule_options must contain rule-code tables.",
        },
    ];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
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
fn given_rule_options_table_when_checking_then_empty_stays_native_and_nonempty_routes_to_python() {
    let test_cases = [
        RuleOptionsCheckRoutingTestCase {
            description: "empty rule options table remains on the native check path",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\n[rule_options]\n",
            expected_exit_code: 0,
            expected_stdout: "Found 0 faults\n",
            expected_stderr: "",
        },
        RuleOptionsCheckRoutingTestCase {
            description: "non-empty rule options table routes to the Python check host",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\n[rule_options.XOP001]\nenabled = true\n",
            expected_exit_code: 2,
            expected_stdout: "",
            expected_stderr: "fensu is not installed beside fensu-cli; install `fensu` or use the CLI package only for `--version`.\n",
        },
    ];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
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
        assert_eq!(
            String::from_utf8_lossy(&output.stdout),
            test_case.expected_stdout,
            "{}",
            test_case.description
        );
        assert_eq!(
            String::from_utf8_lossy(&output.stderr),
            test_case.expected_stderr,
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
