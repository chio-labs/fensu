use std::fs;

use crate::helpers::{create_directory, run_check, run_check_with, write, write_bytes};
use crate::test_types::{
    CheckCacheTestCase, CheckCleanupTestCase, CheckPreservationTestCase,
    PreExecutionCleanupTestCase,
};

const CONFIG: &str =
    "roots = [\"src\"]\ntests = [\"tests\"]\ntooling = [\"scripts\"]\nselect = [\"FFA\"]\n";

#[test]
fn given_configured_roots_when_check_finishes_then_only_empty_and_bytecode_only_trees_are_removed()
{
    let test_cases = [
        CheckCleanupTestCase {
            description: "successful check preserves its exit code while cleaning",
            source: "value: int = 1\n",
            expected_exit_code: 0,
        },
        CheckCleanupTestCase {
            description: "failing check preserves its exit code while cleaning",
            source: "def broken(value):\n    return value\n",
            expected_exit_code: 1,
        },
    ];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        write(
            repository.path().join("src/package/module.py"),
            test_case.source,
        );
        write_bytes(
            repository
                .path()
                .join("src/package/__pycache__/module.cpython-312.pyc"),
            b"live cache",
        );
        write_bytes(
            repository
                .path()
                .join("src/stale/nested/__pycache__/removed.cpython-312.pyc"),
            b"stale cache",
        );
        write_bytes(
            repository
                .path()
                .join("src/stale/nested/__pycache__/removed.cpython-312.pyo"),
            b"stale optimized cache",
        );
        write_bytes(
            repository
                .path()
                .join("src/protected/__pycache__/marker.txt"),
            b"unknown",
        );
        write_bytes(
            repository
                .path()
                .join("src/protected/__pycache__/module.cpython-312.pyc"),
            b"protected cache",
        );
        write_bytes(
            repository.path().join("outside/__pycache__/outside.pyc"),
            b"outside",
        );
        create_directory(repository.path().join("src/empty/nested"));
        create_directory(repository.path().join("tests/empty/nested"));
        create_directory(repository.path().join("scripts/empty/nested"));

        let output = run_check(repository.path());

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: stdout={} stderr={}",
            test_case.description,
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(!repository.path().join("src/empty").exists());
        assert!(!repository.path().join("tests/empty").exists());
        assert!(!repository.path().join("scripts/empty").exists());
        assert!(!repository.path().join("src/stale").exists());
        assert!(repository.path().join("src").is_dir());
        assert!(repository.path().join("tests").is_dir());
        assert!(repository.path().join("scripts").is_dir());
        assert!(repository
            .path()
            .join("src/package/__pycache__/module.cpython-312.pyc")
            .is_file());
        assert!(repository
            .path()
            .join("src/protected/__pycache__/marker.txt")
            .is_file());
        assert!(repository
            .path()
            .join("src/protected/__pycache__/module.cpython-312.pyc")
            .is_file());
        assert!(repository
            .path()
            .join("outside/__pycache__/outside.pyc")
            .is_file());
    }
}

#[cfg(unix)]
#[test]
fn given_symlinked_tree_when_check_finishes_then_link_and_target_are_preserved() {
    use std::os::unix::fs::symlink;

    let test_cases = [CheckPreservationTestCase {
        description: "cleanup does not traverse symlinked directories",
        expected_exit_code: 0,
        expected_path: "outside/empty",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        write(
            repository.path().join("src/package/module.py"),
            "value: int = 1\n",
        );
        create_directory(repository.path().join(test_case.expected_path));
        symlink(
            repository.path().join("outside"),
            repository.path().join("src/linked"),
        )
        .expect("fixture symlink");

        let output = run_check(repository.path());

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            fs::symlink_metadata(repository.path().join("src/linked"))
                .expect("symlink metadata")
                .file_type()
                .is_symlink(),
            "{}",
            test_case.description
        );
        assert!(
            repository.path().join(test_case.expected_path).is_dir(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_active_source_cache_when_bytecode_changes_then_native_check_cache_stays_warm() {
    let test_cases = [CheckCacheTestCase {
        description: "bytecode changes do not invalidate the native check cache",
        expected_exit_code: 0,
        expected_cold_fragment: "misses=1",
        expected_warm_fragment: "hits=1 misses=0",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        write(
            repository.path().join("src/package/module.py"),
            "value: int = 1\n",
        );
        let cache_path = repository
            .path()
            .join("src/package/__pycache__/module.cpython-312.pyc");
        write_bytes(&cache_path, b"first cache");

        let cold = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
        write_bytes(&cache_path, b"changed cache");
        let warm = run_check_with(repository.path(), &["--cache", "--cache-stats"]);

        assert_eq!(
            cold.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&cold.stderr).contains(test_case.expected_cold_fragment),
            "{}",
            test_case.description
        );
        assert_eq!(
            warm.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&warm.stderr).contains(test_case.expected_warm_fragment),
            "{}",
            test_case.description
        );
        assert_eq!(cold.stdout, warm.stdout, "{}", test_case.description);
        assert!(cache_path.is_file(), "{}", test_case.description);
    }
}

#[test]
fn given_preserved_cache_input_when_stub_changes_then_native_check_cache_is_invalidated() {
    let test_cases = [CheckCacheTestCase {
        description: "preserved stubs beneath bytecode directories remain cache inputs",
        expected_exit_code: 0,
        expected_cold_fragment: "misses=1",
        expected_warm_fragment: "misses=1",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        write(
            repository.path().join("src/package/module.py"),
            "value: int = 1\n",
        );
        let stub_path = repository
            .path()
            .join("src/package/__pycache__/contract.pyi");
        write(&stub_path, "value: int\n");

        let cold = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
        write(&stub_path, "value: str\n");
        let warm = run_check_with(repository.path(), &["--cache", "--cache-stats"]);

        assert_eq!(
            cold.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&cold.stderr).contains(test_case.expected_cold_fragment),
            "{}",
            test_case.description
        );
        assert_eq!(
            warm.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&warm.stderr).contains(test_case.expected_warm_fragment),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_pre_execution_exit_when_checking_then_cleanup_does_not_mutate_repository() {
    let test_cases = [
        PreExecutionCleanupTestCase {
            description: "check help is read-only",
            config: CONFIG,
            arguments: &["--help"],
            expected_exit_code: 0,
            expected_path: "src/empty/nested",
        },
        PreExecutionCleanupTestCase {
            description: "invalid check arguments are read-only",
            config: CONFIG,
            arguments: &["--unknown"],
            expected_exit_code: 2,
            expected_path: "src/empty/nested",
        },
        PreExecutionCleanupTestCase {
            description: "custom host launch failure is read-only",
            config: "roots = [\"src\"]\nrule_modules = [\"missing.policy\"]\nselect = [\"X\"]\n",
            arguments: &["--no-cache"],
            expected_exit_code: 2,
            expected_path: "src/empty/nested",
        },
    ];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
        write(
            repository.path().join("src/package/module.py"),
            "value: int = 1\n",
        );
        create_directory(repository.path().join(test_case.expected_path));

        let output = run_check_with(repository.path(), test_case.arguments);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: stderr={}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(
            repository.path().join(test_case.expected_path).is_dir(),
            "{}",
            test_case.description
        );
    }
}
