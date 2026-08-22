//! Structure-checker process contract.

use crate::helpers;
use crate::test_types;

#[test]
fn given_command_cases_when_running_then_returns_documented_streams_and_statuses() {
    let test_cases = [
        test_types::CommandTestCase {
            description: "help",
            arguments: vec!["--help"],
            expected_status: 0,
            expected_stdout: "Usage: fensu-structure-checker",
            expected_stderr: "",
        },
        test_types::CommandTestCase {
            description: "unknown argument",
            arguments: vec!["--unknown"],
            expected_status: 2,
            expected_stdout: "",
            expected_stderr: "error: unknown argument --unknown",
        },
    ];

    for test_case in &test_cases {
        let output = helpers::run_checker(test_case);
        let stdout = String::from_utf8(output.stdout).expect("stdout is UTF-8");
        let stderr = String::from_utf8(output.stderr).expect("stderr is UTF-8");
        assert_eq!(
            output.status.code(),
            Some(test_case.expected_status),
            "case failed: {}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_stdout),
            "case failed: {}\nstdout: {stdout}",
            test_case.description
        );
        assert!(
            stderr.contains(test_case.expected_stderr),
            "case failed: {}\nstderr: {stderr}",
            test_case.description
        );
    }
}

#[test]
fn given_explicit_consumer_config_when_running_then_applies_configured_boundary() {
    let test_cases = [test_types::CommandTestCase {
        description: "explicit consumer config",
        arguments: Vec::new(),
        expected_status: 1,
        expected_stdout: "help: consume shared SQL fact rows",
        expected_stderr: "",
    }];

    for test_case in &test_cases {
        let output = helpers::run_configured_checker();
        let stdout = String::from_utf8(output.stdout).expect("stdout is UTF-8");
        let stderr = String::from_utf8(output.stderr).expect("stderr is UTF-8");
        assert_eq!(
            output.status.code(),
            Some(test_case.expected_status),
            "case failed: {}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_stdout),
            "case failed: {}\nstdout: {stdout}",
            test_case.description
        );
        assert!(
            stderr.contains(test_case.expected_stderr),
            "case failed: {}\nstderr: {stderr}",
            test_case.description
        );
    }
}

#[cfg(unix)]
#[test]
fn given_config_symlink_escape_when_running_then_rejects_it_before_loading() {
    let test_cases = [test_types::CommandTestCase {
        description: "config symlink escape",
        arguments: Vec::new(),
        expected_status: 2,
        expected_stdout: "",
        expected_stderr: "escapes repository root",
    }];
    for test_case in &test_cases {
        let output = helpers::run_escaped_config_checker();
        let stderr = String::from_utf8(output.stderr).expect("stderr is UTF-8");
        assert_eq!(
            output.status.code(),
            Some(test_case.expected_status),
            "{}",
            test_case.description
        );
        assert!(
            output.stdout.is_empty() && test_case.expected_stdout.is_empty(),
            "{}",
            test_case.description
        );
        assert!(
            stderr.contains(test_case.expected_stderr),
            "{}: {stderr}",
            test_case.description
        );
    }
}
