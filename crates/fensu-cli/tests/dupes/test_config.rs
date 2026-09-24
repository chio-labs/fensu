use std::process::Command;

use crate::helpers::{
    cluster_members, copies, json_report, run_dupes, summary, text, with_dupes, write, write_files,
    PYTHON_CONFIG,
};
use crate::test_types::{ClusterTestCase, CommandOutputTestCase};

#[test]
fn given_dupes_configuration_when_reporting_then_exclusions_and_allowlist_apply() {
    let test_cases = [
        ClusterTestCase {
            description: "tooling is analysed by default",
            config: with_dupes(""),
            files: copies(),
            arguments: &["--json"],
            expected_clusters: vec![vec!["scripts/summary.py", "src/shop/billing/summary.py", "src/shop/orders/summary.py"]],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 0,
        },
        ClusterTestCase {
            description: "excluded paths are not analysed",
            config: with_dupes("[dupes]\nexclude = [\"scripts/**\"]\n"),
            files: copies(),
            arguments: &["--json"],
            expected_clusters: vec![vec!["src/shop/billing/summary.py", "src/shop/orders/summary.py"]],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 0,
        },
        ClusterTestCase {
            description: "an allowlist covering both sides hides the pair",
            config: with_dupes("[dupes]\nexclude = [\"scripts/**\"]\n\n[[dupes.allowlist]]\npaths = [\"src/shop/orders/*\", \"src/shop/billing/*\"]\nreason = \"Order and billing summaries intentionally mirror one report contract.\"\n"),
            files: copies(),
            arguments: &["--json"],
            expected_clusters: vec![],
            expected_allowlisted_pairs: 1,
            expected_contract_exempt_members: 0,
        },
        ClusterTestCase {
            description: "an allowlist covering one side keeps the pair",
            config: with_dupes("[dupes]\nexclude = [\"scripts/**\"]\n\n[[dupes.allowlist]]\npaths = [\"src/shop/orders/*\"]\nreason = \"Order summaries mirror each other.\"\n"),
            files: copies(),
            arguments: &["--json"],
            expected_clusters: vec![vec!["src/shop/billing/summary.py", "src/shop/orders/summary.py"]],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 0,
        },
        ClusterTestCase {
            description: "configured tests are skipped unless requested",
            config: format!("{PYTHON_CONFIG}\n[dupes]\n"),
            files: vec![
                ("src/shop/orders/summary.py", summary("")),
                ("tests/test_summary.py", summary("")),
            ],
            arguments: &["--json", "--include-tests"],
            expected_clusters: vec![vec!["src/shop/orders/summary.py", "tests/test_summary.py"]],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 0,
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), &test_case.config);
        write_files(repository.path(), &test_case.files);

        let output = run_dupes(repository.path(), test_case.arguments);
        let report = json_report(&output);

        assert_eq!(
            output.status.code(),
            Some(0),
            "{}: {}",
            test_case.description,
            text(&output.stderr)
        );
        assert_eq!(
            cluster_members(&report),
            test_case.expected_clusters,
            "{}",
            test_case.description
        );
        assert_eq!(
            report["allowlisted_pairs"],
            serde_json::json!(test_case.expected_allowlisted_pairs),
            "{}",
            test_case.description
        );
        assert_eq!(
            report["contract_exempt_members"],
            serde_json::json!(test_case.expected_contract_exempt_members),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_configuration_or_arguments_when_running_dupes_then_errors_exit_two() {
    let test_cases = [
        CommandOutputTestCase {
            description: "dupes must be a table",
            config: format!("dupes = 1\n{PYTHON_CONFIG}"),
            files: copies(),
            arguments: &[],
            expected_exit_code: 2,
            expected_stdout: &[],
            expected_stderr: &["Config key dupes must be a table."],
        },
        CommandOutputTestCase {
            description: "unknown dupes keys are rejected",
            config: with_dupes("[dupes]\nignore = []\n"),
            files: copies(),
            arguments: &[],
            expected_exit_code: 2,
            expected_stdout: &[],
            expected_stderr: &["Unknown dupes config key(s): ignore."],
        },
        CommandOutputTestCase {
            description: "allowlist entries need a reason",
            config: with_dupes("[[dupes.allowlist]]\npaths = [\"src/**\"]\nreason = \"  \"\n"),
            files: copies(),
            arguments: &[],
            expected_exit_code: 2,
            expected_stdout: &[],
            expected_stderr: &["Config key dupes.allowlist entry 1 needs a non-empty reason."],
        },
        CommandOutputTestCase {
            description: "allowlist entries need paths",
            config: with_dupes("[[dupes.allowlist]]\npaths = []\nreason = \"Mirrors.\"\n"),
            files: copies(),
            arguments: &[],
            expected_exit_code: 2,
            expected_stdout: &[],
            expected_stderr: &["Config key dupes.allowlist entry 1 needs a non-empty paths list of path globs."],
        },
        CommandOutputTestCase {
            description: "contract specs name a relative Python path and class",
            config: with_dupes("[[dupes.contract_exemptions]]\ncontract = \"/src/shop/contract.py:Exporter\"\npaths = [\"src/**\"]\nreason = \"Exporters mirror one contract.\"\n"),
            files: copies(),
            arguments: &[],
            expected_exit_code: 2,
            expected_stdout: &[],
            expected_stderr: &["Config key dupes.contract_exemptions entry 1 contract must be 'relative/path.py:ClassName'."],
        },
        CommandOutputTestCase {
            description: "a missing contract class in an existing file is an error",
            config: with_dupes("[[dupes.contract_exemptions]]\ncontract = \"src/shop/orders/summary.py:Exporter\"\npaths = [\"src/**\"]\nreason = \"Exporters mirror one contract.\"\n"),
            files: copies(),
            arguments: &[],
            expected_exit_code: 2,
            expected_stdout: &[],
            expected_stderr: &["class src/shop/orders/summary.py:Exporter was not found in the analysed source."],
        },
        CommandOutputTestCase {
            description: "unknown revisions are reported",
            config: with_dupes(""),
            files: copies(),
            arguments: &["--since", "no-such-revision"],
            expected_exit_code: 2,
            expected_stdout: &[],
            expected_stderr: &["fensu dupes: analysis failed: --since revision no-such-revision is not a commit"],
        },
        CommandOutputTestCase {
            description: "non-positive top is a usage error",
            config: with_dupes(""),
            files: copies(),
            arguments: &["--top", "0"],
            expected_exit_code: 2,
            expected_stdout: &[],
            expected_stderr: &["fensu dupes: error: argument --top: must be an integer of at least 1"],
        },
        CommandOutputTestCase {
            description: "similarity must be in range",
            config: with_dupes(""),
            files: copies(),
            arguments: &["--min-similarity", "1.5"],
            expected_exit_code: 2,
            expected_stdout: &[],
            expected_stderr: &["argument --min-similarity: must be in (0, 1]"],
        },
        CommandOutputTestCase {
            description: "unknown languages are usage errors",
            config: with_dupes(""),
            files: copies(),
            arguments: &["--lang", "cobol"],
            expected_exit_code: 2,
            expected_stdout: &[],
            expected_stderr: &["argument --lang: invalid choice: 'cobol'"],
        },
        CommandOutputTestCase {
            description: "help documents the advisory exit contract",
            config: with_dupes(""),
            files: copies(),
            arguments: &["--help"],
            expected_exit_code: 0,
            expected_stdout: &["usage: fensu dupes", "Findings never fail the command"],
            expected_stderr: &[],
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), &test_case.config);
        write_files(repository.path(), &test_case.files);

        let output = run_dupes(repository.path(), test_case.arguments);
        let stdout = text(&output.stdout);
        let stderr = text(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stderr}",
            test_case.description
        );
        assert!(
            test_case
                .expected_stdout
                .iter()
                .all(|fragment| stdout.contains(fragment)),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            test_case
                .expected_stderr
                .iter()
                .all(|fragment| stderr.contains(fragment)),
            "{}: {stderr}",
            test_case.description
        );
    }
}

#[test]
fn given_dupes_section_when_checking_then_target_configuration_stays_valid() {
    let test_cases = [
        CommandOutputTestCase {
            description: "legacy flat configuration",
            config: format!("{PYTHON_CONFIG}select = [\"FFA\"]\n\n[dupes]\nexclude = [\"scripts/**\"]\n"),
            files: vec![("src/shop/__init__.py", String::new())],
            arguments: &["check", "--no-cache"],
            expected_exit_code: 0,
            expected_stdout: &["Found 0 faults"],
            expected_stderr: &[],
        },
        CommandOutputTestCase {
            description: "explicit targets",
            config: "[targets.app]\nanalyzer = \"python\"\nroots = [\"src/shop\"]\nselect = [\"FFA\"]\n\n[dupes]\nexclude = [\"scripts/**\"]\n".to_owned(),
            files: vec![("src/shop/__init__.py", String::new())],
            arguments: &["check", "--no-cache"],
            expected_exit_code: 0,
            expected_stdout: &["Found 0 faults"],
            expected_stderr: &[],
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), &test_case.config);
        write_files(repository.path(), &test_case.files);

        let output = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(test_case.arguments)
            .current_dir(repository.path())
            .env("FENSU_PYTHON", repository.path().join("missing-python"))
            .env("NO_COLOR", "1")
            .output()
            .expect("native check process runs");
        let stdout = text(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            text(&output.stderr)
        );
        assert!(
            test_case
                .expected_stdout
                .iter()
                .all(|fragment| stdout.contains(fragment)),
            "{}: {stdout}",
            test_case.description
        );
    }
}
