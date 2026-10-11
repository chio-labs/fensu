//! File placement checks observe mutations outside configured source roots.

use crate::helpers::{run_check_with, write};
use crate::test_types::RustPlacementCacheTestCase;

#[test]
fn given_clean_placement_checks_when_filesystem_changes_then_cached_clean_output_is_not_reused() {
    let test_cases = [
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
            !String::from_utf8_lossy(&changed.stderr).contains("Cache: hits="),
            "{}",
            test_case.description
        );
    }
}
