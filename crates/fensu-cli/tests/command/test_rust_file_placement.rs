//! File placement checks observe mutations outside configured source roots.

use crate::helpers::{run_check_with, write};
use crate::test_types::RustParentIgnoreTestCase;
use crate::test_types::{RustPlacementCacheHitTestCase, RustPlacementCacheTestCase};

#[test]
fn given_clean_placement_checks_when_filesystem_changes_then_cached_clean_output_is_not_reused() {
    let test_cases = [
        RustPlacementCacheTestCase {
            description: "changed workspace ignore file",
            path: "../../.gitignore",
            prepare: |package, path| {
                write(package.join("notes.txt"), "ignored resource");
                write(package.join(path), "crates/example/notes.txt\n");
            },
            mutate: |package, path| write(package.join(path), ""),
            expected_code: "FPRSR311",
            expected_path: "notes.txt",
        },
        RustPlacementCacheTestCase {
            description: "changed intermediate ignore file",
            path: "../.gitignore",
            prepare: |package, path| {
                write(package.join("notes.txt"), "ignored resource");
                write(package.join(path), "example/notes.txt\n");
            },
            mutate: |package, path| write(package.join(path), ""),
            expected_code: "FPRSR311",
            expected_path: "notes.txt",
        },
        RustPlacementCacheTestCase {
            description: "embedded target changes from file to directory",
            path: "src/orders/data.txt",
            prepare: |_, _| {},
            mutate: |package, path| {
                std::fs::remove_file(package.join(path)).expect("remove target file");
                std::fs::create_dir(package.join(path)).expect("replace with directory");
            },
            expected_code: "FPRSL106",
            expected_path: "orders/constants.rs",
        },
        #[cfg(unix)]
        RustPlacementCacheTestCase {
            description: "symlink target moves outside the domain",
            path: "src/orders/data.txt",
            prepare: |package, path| {
                std::fs::remove_file(package.join(path)).expect("replace target");
                write(package.join("src/orders/local.txt"), "resource");
                write(package.join(".hidden/remote.txt"), "resource");
                std::os::unix::fs::symlink("local.txt", package.join(path))
                    .expect("initial target link");
            },
            mutate: |package, path| {
                std::fs::remove_file(package.join(path)).expect("replace target link");
                std::os::unix::fs::symlink("../../.hidden/remote.txt", package.join(path))
                    .expect("changed target link");
            },
            expected_code: "FPRSL106",
            expected_path: "orders/constants.rs",
        },
        RustPlacementCacheTestCase {
            description: "new stray file",
            path: "notes.txt",
            prepare: |_, _| {},
            mutate: |package, path| write(package.join(path), "resource"),
            expected_code: "FPRSR311",
            expected_path: "notes.txt",
        },
        RustPlacementCacheTestCase {
            description: "new data directory",
            path: "data/value.txt",
            prepare: |_, _| {},
            mutate: |package, path| write(package.join(path), "resource"),
            expected_code: "FPRSR311",
            expected_path: "example/data",
        },
        RustPlacementCacheTestCase {
            description: "stray Rust file outside roots",
            path: "scratch.rs",
            prepare: |_, _| {},
            mutate: |package, path| write(package.join(path), "resource"),
            expected_code: "FPRSR311",
            expected_path: "scratch.rs",
        },
        RustPlacementCacheTestCase {
            description: "directory ending in Rust suffix",
            path: "resources.rs/value.txt",
            prepare: |_, _| {},
            mutate: |package, path| write(package.join(path), "resource"),
            expected_code: "FPRSR311",
            expected_path: "resources.rs",
        },
        RustPlacementCacheTestCase {
            description: "removed embedded target",
            path: "src/orders/data.txt",
            prepare: |_, _| {},
            mutate: |package, path| {
                std::fs::remove_file(package.join(path)).expect("remove target")
            },
            expected_code: "FPRSL106",
            expected_path: "orders/constants.rs",
        },
        RustPlacementCacheTestCase {
            description: "changed applicable ignore file",
            path: ".gitignore",
            prepare: |package, _| {
                write(package.join("notes.txt"), "ignored resource");
                write(package.join(".gitignore"), "notes.txt\n");
            },
            mutate: |package, path| write(package.join(path), ""),
            expected_code: "FPRSR311",
            expected_path: "notes.txt",
        },
    ];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("fixture repository");
        write(
            repository.path().join("Cargo.toml"),
            "[workspace]\nmembers = ['crates/example']\nresolver = '2'\n",
        );
        write(repository.path().join("fensu.toml"), &format!("[targets.rust]\nanalyzer = 'rust'\nroots = ['crates/example/src']\ntests = []\ntooling = []\nrule_packs = ['rust']\nselect = ['{}']\n", test_case.expected_code));
        let package = repository.path().join("crates/example");
        write(
            package.join("Cargo.toml"),
            "[package]\nname = 'example'\nversion = '0.1.0'\nedition = '2021'\n",
        );
        write(package.join("src/lib.rs"), "");
        write(
            package.join("src/orders/constants.rs"),
            "const DATA: &str = include_str!(\"data.txt\");\n",
        );
        write(package.join("src/orders/data.txt"), "resource");
        (test_case.prepare)(&package, test_case.path);
        let arguments = ["--cache", "--cache-stats"];
        let initial = run_check_with(repository.path(), &arguments);
        assert!(
            initial.status.success(),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&initial.stdout)
        );
        let unchanged = run_check_with(repository.path(), &arguments);
        assert!(unchanged.status.success(), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&unchanged.stderr).contains("Cache: hits=2 misses=0"),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&unchanged.stderr)
        );
        (test_case.mutate)(&package, test_case.path);
        let changed = run_check_with(repository.path(), &arguments);
        let stdout = String::from_utf8_lossy(&changed.stdout);
        assert_eq!(
            changed.status.code(),
            Some(1),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_code),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_path),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&changed.stderr).contains("Cache: hits=0 misses="),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_default_rust_and_mixed_targets_when_unchanged_then_second_run_hits_result_cache() {
    let test_cases = [
        RustPlacementCacheHitTestCase { description: "default Rust pack", extra_config: "", expected_hits: "Cache: hits=1 misses=0" },
        RustPlacementCacheHitTestCase { description: "mixed Rust and Python targets", extra_config: "[targets.python]\nanalyzer = 'python'\nroots = ['python']\ntests = []\ntooling = []\nselect = ['FFA001']\n", expected_hits: "Cache: hits=2 misses=0" },
    ];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("fixture repository");
        write(repository.path().join("Cargo.toml"), "[workspace]\nmembers = ['crates/example']\nresolver = '2'\n[workspace.package]\nedition = '2021'\nlicense = 'MIT'\npublish = false\n[workspace.lints.rust]\nunsafe_code = 'forbid'\nunreachable_pub = 'deny'\nunused_must_use = 'deny'\n[workspace.lints.clippy]\nawait_holding_lock = 'deny'\n");
        write(
            repository.path().join("Cargo.lock"),
            "version = 4\n[[package]]\nname = 'example'\nversion = '0.1.0'\n",
        );
        write(repository.path().join("crates/example/Cargo.toml"), "[package]\nname = 'example'\nversion = '0.1.0'\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n[lints]\nworkspace = true\n");
        write(
            repository.path().join("crates/example/src/lib.rs"),
            "#![forbid(unsafe_code)]\n",
        );
        write(
            repository.path().join("python/value.py"),
            "def value() -> int:\n    return 1\n",
        );
        write(repository.path().join("fensu.toml"), &format!("[targets.rust]\nanalyzer = 'rust'\nroots = ['crates/example/src']\ntests = []\ntooling = []\nrule_packs = ['rust']\nselect = ['FPRS']\n{}", test_case.extra_config));
        let initial = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
        assert!(
            initial.status.success(),
            "{}: {} {}",
            test_case.description,
            String::from_utf8_lossy(&initial.stdout),
            String::from_utf8_lossy(&initial.stderr)
        );
        let unchanged = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
        assert_eq!(
            unchanged.stdout, initial.stdout,
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&unchanged.stderr).contains(test_case.expected_hits),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&unchanged.stderr)
        );
    }
}
#[test]
fn given_nested_cargo_workspace_when_repository_ignore_changes_then_cached_result_invalidates() {
    let test_cases = [RustParentIgnoreTestCase {
        description: "Git root ignore applies above the Cargo workspace",
        expected_code: "FPRSR311",
        expected_hits: "Cache: hits=1 misses=0",
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("fixture repository");
        write(repository.path().join(".git/keep"), "");
        write(
            repository.path().join(".gitignore"),
            "workspace/crates/example/notes.txt\n",
        );
        write(
            repository.path().join("workspace/Cargo.toml"),
            "[workspace]\nmembers = ['crates/example']\nresolver = '2'\n",
        );
        write(
            repository
                .path()
                .join("workspace/crates/example/Cargo.toml"),
            "[package]\nname = 'example'\nversion = '0.1.0'\nedition = '2021'\n",
        );
        write(
            repository
                .path()
                .join("workspace/crates/example/src/lib.rs"),
            "",
        );
        write(
            repository.path().join("workspace/crates/example/notes.txt"),
            "resource",
        );
        write(repository.path().join("fensu.toml"), "[targets.rust]\nanalyzer = 'rust'\nroot = 'workspace'\nroots = ['crates/example/src']\ntests = []\ntooling = []\nrule_packs = ['rust']\nselect = ['FPRSR311']\n");
        let initial = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
        assert!(
            initial.status.success(),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&initial.stdout)
        );
        let unchanged = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
        assert!(
            String::from_utf8_lossy(&unchanged.stderr).contains(test_case.expected_hits),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&unchanged.stderr)
        );
        write(repository.path().join(".gitignore"), "");
        let changed = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
        assert_eq!(changed.status.code(), Some(1), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&changed.stdout).contains(test_case.expected_code),
            "{}",
            test_case.description
        );
    }
}
#[cfg(unix)]
#[test]
fn given_unreadable_ignore_when_checking_then_observation_failure_only_bypasses_requested_cache() {
    use std::os::unix::fs::PermissionsExt;

    let test_cases = [
        crate::test_types::RustObservationFailureTestCase {
            description: "cache requested for placement",
            selection: "select = ['FPRSR311']",
            arguments: &["--cache", "--cache-stats"],
            expected_exit: 1,
            expected_output: "FPRSR311",
            expected_bypass: true,
            expected_error_reason: true,
        },
        crate::test_types::RustObservationFailureTestCase {
            description: "cache explicitly disabled",
            selection: "select = ['FPRSR311']",
            arguments: &["--no-cache", "--cache-stats"],
            expected_exit: 1,
            expected_output: "FPRSR311",
            expected_bypass: false,
            expected_error_reason: false,
        },
        crate::test_types::RustObservationFailureTestCase {
            description: "placement rules not selected",
            selection: "select = ['FPRSH902']",
            arguments: &["--cache", "--cache-stats"],
            expected_exit: 0,
            expected_output: "Found 0 faults",
            expected_bypass: false,
            expected_error_reason: false,
        },
        crate::test_types::RustObservationFailureTestCase {
            description: "ignored placement rules",
            selection:
                "select = ['FPRSH902', 'FPRSR311', 'FPRSL106']\nignore = ['FPRSR311', 'FPRSL106']",
            arguments: &["--cache", "--cache-stats"],
            expected_exit: 0,
            expected_output: "Found 0 faults",
            expected_bypass: false,
            expected_error_reason: false,
        },
        crate::test_types::RustObservationFailureTestCase {
            description: "displayed placement warnings",
            selection: "select = ['FPRSH902']\nwarn = ['FPRSR311']",
            arguments: &["--cache", "--cache-stats", "--warn"],
            expected_exit: 0,
            expected_output: "FPRSR311",
            expected_bypass: true,
            expected_error_reason: true,
        },
        crate::test_types::RustObservationFailureTestCase {
            description: "placement warnings not requested",
            selection: "select = ['FPRSH902']\nwarn = ['FPRSR311']",
            arguments: &["--cache", "--cache-stats"],
            expected_exit: 0,
            expected_output: "Found 0 faults",
            expected_bypass: false,
            expected_error_reason: false,
        },
    ];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("fixture repository");
        write(
            repository.path().join("Cargo.toml"),
            "[workspace]\nmembers = ['crates/example']\nresolver = '2'\n",
        );
        write(
            repository.path().join("crates/example/Cargo.toml"),
            "[package]\nname = 'example'\nversion = '0.1.0'\nedition = '2021'\n",
        );
        write(repository.path().join("crates/example/src/lib.rs"), "");
        write(repository.path().join("fensu.toml"), &format!("[targets.rust]\nanalyzer = 'rust'\nroots = ['crates/example/src']\ntests = []\ntooling = []\nrule_packs = ['rust']\n{}\n", test_case.selection));
        let ignore = repository.path().join("crates/example/.gitignore");
        write(&ignore, "notes.txt\n");
        std::fs::set_permissions(&ignore, std::fs::Permissions::from_mode(0o000))
            .expect("make ignore unreadable");
        let output = run_check_with(repository.path(), test_case.arguments);
        std::fs::set_permissions(&ignore, std::fs::Permissions::from_mode(0o644))
            .expect("restore ignore permissions");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_output),
            "{}: {stdout}",
            test_case.description
        );
        assert_eq!(
            stderr.contains("Cache bypassed for target rust:"),
            test_case.expected_bypass,
            "{}: {stderr}",
            test_case.description
        );
        assert_eq!(
            stderr.contains("placement observations unavailable: cannot read ignore input"),
            test_case.expected_error_reason,
            "{}: {stderr}",
            test_case.description
        );
    }
}
