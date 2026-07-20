use std::process::Command;

use crate::helpers::{assert_success, run, write};
use crate::test_types::{InvalidMemoryArgumentsTestCase, NativeMemoryCommandTestCase};

const CONFIG: &str =
    "roots = [\"src\"]\n[experimental]\nmemory = true\n[memory.tasks]\narchive_after_days = 7\n";
const NOTE_PATH: &str = ".ai/knowledge/repo/notes/20260719T120000_000000Z__NOTE-native-proof.md";

#[test]
fn given_enabled_memory_when_running_every_command_then_binary_never_requires_python() {
    let test_cases = [NativeMemoryCommandTestCase {
        description: "all built-in memory commands execute without Python",
        expected_exit_code: 0,
        expected_output: "{\"columns\":[\"value\",\"text\",\"ratio\"],\"types\":[\"Integer\",\"Text\",\"Real\"],\"rows\":[[7,\"café\",1.0]],\"truncated\":false}\n",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        write(
            repository.path().join(NOTE_PATH),
            "# Café Native Proof\n\nPersistent context.\n",
        );

        let summary = run(repository.path(), &[]);
        assert_success(&summary, "Tasks:");
        assert_eq!(
            summary.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(summary.stderr.is_empty(), "{}", test_case.description);

        let check = run(repository.path(), &["check"]);
        assert_success(&check, "Found 0 faults\n");

        let sql = run(
            repository.path(),
            &[
                "sql",
                "SELECT 7 AS value, 'café' AS text, CAST(1 AS REAL) AS ratio",
                "--format",
                "json",
            ],
        );
        assert_eq!(
            String::from_utf8(sql.stdout).expect("SQL stdout is UTF-8"),
            test_case.expected_output,
            "{}",
            test_case.description
        );
        assert!(sql.stderr.is_empty(), "{}", test_case.description);

        let csv = run(
            repository.path(),
            &["sql", "SELECT 'a,\"b\"' AS text", "--format", "csv"],
        );
        assert_eq!(
            csv.stdout, b"text\r\n\"a,\"\"b\"\"\"\r\n",
            "{}",
            test_case.description
        );

        let schema = run(repository.path(), &["schema", "current_tasks"]);
        assert_success(&schema, "memory.current_tasks (view)\n");

        let graph = run(
            repository.path(),
            &["graph", "native-proof", "--format", "json"],
        );
        assert_eq!(
            String::from_utf8(graph.stdout).expect("graph stdout is UTF-8"),
            "{\"depth\":2,\"direction\":\"outbound\",\"edges\":[],\"include_archived\":false,\"limits\":{\"max_edges\":100,\"max_nodes\":50},\"nodes\":[{\"archive_state\":\"active\",\"artifact_kind\":\"note\",\"basename\":\"20260719T120000_000000Z__NOTE-native-proof.md\",\"depth\":0,\"identity\":\"note:20260719T120000_000000Z\",\"repository_relative_path\":\".ai/knowledge/repo/notes/20260719T120000_000000Z__NOTE-native-proof.md\",\"root\":true,\"slug\":\"native-proof\",\"title\":\"Caf\\u00e9 Native Proof\"}],\"pattern\":\"native-proof\",\"relationships\":[],\"roots\":[\"note:20260719T120000_000000Z\"],\"selection\":\"exact\",\"truncated\":{\"edges\":false,\"nodes\":false}}\n",
            "{}",
            test_case.description
        );
        assert!(graph.stderr.is_empty(), "{}", test_case.description);

        let sync = run(repository.path(), &["sync"]);
        assert_success(&sync, "Memory sync:");

        let rebuild = run(repository.path(), &["rebuild"]);
        assert_success(&rebuild, "Memory rebuilt:");

        let automatic_archive = run(repository.path(), &["archive"]);
        assert_success(&automatic_archive, "Memory archive: no eligible sources");

        let terminator = run(repository.path(), &["archive", "--", "--yes"]);
        assert_eq!(
            terminator.status.code(),
            Some(2),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&terminator.stderr).contains("--yes"),
            "{}",
            test_case.description
        );

        let archive = run(repository.path(), &["archive", NOTE_PATH]);
        assert_success(&archive, "Memory archived:");
        assert!(
            !repository.path().join(NOTE_PATH).exists(),
            "{}",
            test_case.description
        );
        assert!(repository
            .path()
            .join(".ai/_archive/knowledge/repo/notes/20260719T120000_000000Z__NOTE-native-proof.md")
            .is_file(), "{}", test_case.description);
    }
}

#[test]
fn given_invalid_memory_source_when_checking_then_findings_use_exit_one_on_stdout() {
    let test_cases = [NativeMemoryCommandTestCase {
        description: "memory check reports one invalid source on stdout",
        expected_exit_code: 1,
        expected_output: "Found 1 fault",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        let bootstrap = run(repository.path(), &[]);
        assert_eq!(
            bootstrap.status.code(),
            Some(0),
            "{}",
            test_case.description
        );
        write(
            repository
                .path()
                .join(".ai/knowledge/repo/notes/20260719T120001_000000Z__NOTE-invalid.md"),
            "Missing title.\n",
        );

        let output = run(repository.path(), &["check", "--color", "never"]);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        let stdout = String::from_utf8(output.stdout).expect("check stdout is UTF-8");
        assert!(stdout.contains("MEM"), "{}", test_case.description);
        assert!(
            stdout.contains(test_case.expected_output),
            "{}",
            test_case.description
        );
        assert!(output.stderr.is_empty(), "{}", test_case.description);
    }
}

#[test]
fn given_disabled_or_conflicting_memory_when_running_then_errors_use_exit_two() {
    let test_cases = [NativeMemoryCommandTestCase {
        description: "disabled and conflicting memory fail before engine execution",
        expected_exit_code: 2,
        expected_output: "Fensu Memory is disabled",
    }];
    for test_case in &test_cases {
        let disabled = tempfile::tempdir().expect("disabled repository");
        write(
            disabled.path().join("fensu.toml"),
            "roots = [\"src\"]\n[experimental]\nmemory = false\n",
        );
        let disabled_output = run(disabled.path(), &["schema"]);
        assert_eq!(
            disabled_output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            disabled_output.stdout.is_empty(),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8(disabled_output.stderr)
                .expect("disabled stderr is UTF-8")
                .contains(test_case.expected_output),
            "{}",
            test_case.description
        );

        let conflicting = tempfile::tempdir().expect("conflicting repository");
        write(conflicting.path().join("fensu.toml"), CONFIG);
        write(conflicting.path().join(".ai/orphan.md"), "# Orphan\n");
        let conflict_output = run(conflicting.path(), &["sync"]);
        assert_eq!(
            conflict_output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8(conflict_output.stderr)
                .expect("conflict stderr is UTF-8")
                .contains("Existing .ai content is not canonical"),
            "{}",
            test_case.description
        );
        assert!(
            !conflicting
                .path()
                .join(".fensu/memory/.bootstrapped")
                .exists(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_archive_retention_when_running_memory_then_config_error_is_actionable() {
    let test_cases = [NativeMemoryCommandTestCase {
        description: "negative archive retention is rejected",
        expected_exit_code: 2,
        expected_output: "archive_after_days must be non-negative",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "roots = [\"src\"]\n[experimental]\nmemory = true\n[memory.tasks]\narchive_after_days = -1\n",
        );

        let output = run(repository.path(), &["archive"]);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8(output.stderr)
                .expect("config stderr is UTF-8")
                .contains(test_case.expected_output),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_memory_help_when_python_is_unavailable_then_native_parser_documents_surface() {
    let test_cases = [NativeMemoryCommandTestCase {
        description: "native help documents every memory command",
        expected_exit_code: 0,
        expected_output: "{archive,check,sync,rebuild,schema,graph,sql}",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");

        let output = run(repository.path(), &["--help"]);

        assert_success(&output, test_case.expected_output);
        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_memory_arguments_when_parsing_then_errors_use_exit_two_without_python() {
    let repository = tempfile::tempdir().expect("temporary repository");
    let test_cases = [
        InvalidMemoryArgumentsTestCase {
            description: "graph depth below minimum",
            arguments: &["graph", "alpha", "--depth", "0"],
            expected_exit_code: 2,
            expected_error: "depth must be between 1 and 5",
        },
        InvalidMemoryArgumentsTestCase {
            description: "unknown graph relationship",
            arguments: &["graph", "alpha", "--relationship", "unknown"],
            expected_exit_code: 2,
            expected_error: "invalid choice: 'unknown'",
        },
        InvalidMemoryArgumentsTestCase {
            description: "SQL limit below minimum",
            arguments: &["sql", "SELECT 1", "--limit", "0"],
            expected_exit_code: 2,
            expected_error: "limit must be between 1 and 1000",
        },
        InvalidMemoryArgumentsTestCase {
            description: "mutually exclusive SQL limits",
            arguments: &["sql", "SELECT 1", "--limit", "2", "--no-limit"],
            expected_exit_code: 2,
            expected_error: "not allowed with argument --limit",
        },
        InvalidMemoryArgumentsTestCase {
            description: "unknown memory command",
            arguments: &["unknown"],
            expected_exit_code: 2,
            expected_error: "invalid choice: 'unknown'",
        },
    ];

    for test_case in &test_cases {
        let output = run(repository.path(), test_case.arguments);
        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(output.stdout.is_empty(), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_error),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_color_controls_when_running_memory_then_no_color_and_machine_output_win() {
    let test_cases = [NativeMemoryCommandTestCase {
        description: "NO_COLOR and machine formats suppress ANSI",
        expected_exit_code: 0,
        expected_output: "Memory synced:",
    }];
    for test_case in &test_cases {
        let colored = tempfile::tempdir().expect("colored repository");
        write(colored.path().join("fensu.toml"), CONFIG);
        let always = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["memory", "--color", "always"])
            .current_dir(colored.path())
            .env("FENSU_PYTHON", colored.path().join("python-does-not-exist"))
            .env_remove("NO_COLOR")
            .output()
            .expect("colored native process runs");
        assert_eq!(
            always.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            always.stdout.windows(4).any(|window| window == b"\x1b[1;"),
            "{}",
            test_case.description
        );

        let plain = run(colored.path(), &["--color", "always"]);
        assert_eq!(
            plain.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(!plain.stdout.contains(&0x1b), "{}", test_case.description);

        let machine = tempfile::tempdir().expect("machine repository");
        write(machine.path().join("fensu.toml"), CONFIG);
        write(
            machine.path().join(NOTE_PATH),
            "# Machine Output\n\nSynchronization evidence.\n",
        );
        let json = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args([
                "memory",
                "sql",
                "SELECT 1 AS value",
                "--format",
                "json",
                "--color",
                "always",
            ])
            .current_dir(machine.path())
            .env("FENSU_PYTHON", machine.path().join("python-does-not-exist"))
            .env_remove("NO_COLOR")
            .output()
            .expect("machine native process runs");
        assert_eq!(
            json.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(!json.stdout.contains(&0x1b), "{}", test_case.description);
        assert!(!json.stderr.contains(&0x1b), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&json.stderr).contains(test_case.expected_output),
            "{}",
            test_case.description
        );
    }
}
