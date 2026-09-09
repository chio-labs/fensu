use crate::helpers::{run_check, run_check_with, write};
use crate::test_types::{
    InvalidCheckConfigTestCase, RustCacheTestCase, RustCheckTestCase, RustMetadataCacheTestCase,
};

const RUST_CONFIG: &str = "[targets.rust]\nanalyzer = \"rust\"\nroots = [\"src\"]\ntests = []\ntooling = []\nrule_packs = [\"rust\"]\nselect = [\"FPRSL302\"]\n";

#[test]
fn given_custom_python_and_rust_options_when_checking_then_native_and_hosted_targets_merge() {
    let test_cases = [crate::test_types::RustMixedTargetTestCase {
        description: "custom Python target and native Rust options coexist",
        expected_exit_code: 1,
        expected_codes: &["FFA001", "FPRSS010"],
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("Cargo.toml"),
            "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        );
        write(
            repository.path().join("src/lib.rs"),
            "pub fn sum(left: usize, right: usize) -> usize { left + right }\n",
        );
        write(
            repository.path().join("python/value.py"),
            "def value(item):\n    return item\n",
        );
        write(repository.path().join("rules/custom.py"), "import ast\nfrom fensu import Family, Fault, RuleContext, rule\n@rule(code='XMIX001', family=Family.CUSTOM, slug='mixed', message='mixed')\ndef mixed(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n    return []\n");
        write(repository.path().join("fensu.toml"), "[targets.python]\nanalyzer = \"python\"\nroots = [\"python\"]\ntests = []\ntooling = []\nselect = [\"FFA001\", \"XMIX001\"]\nrule_paths = [\"rules/custom.py\"]\n[targets.rust]\nanalyzer = \"rust\"\nroots = [\"src\"]\ntests = []\ntooling = []\nrule_packs = [\"rust\"]\nselect = [\"FPRSS010\"]\n[targets.rust.rule_options.FPRSS010]\nmax_arguments = 1\n");
        let output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", crate::helpers::workspace_python())
            .output()
            .expect("mixed check runs");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        for code in test_case.expected_codes {
            assert!(stdout.contains(code), "{}: {stdout}", test_case.description);
        }
    }
}

#[test]
fn given_rust_target_when_checking_then_structure_engine_uses_pack_policy_and_exceptions() {
    let test_cases = [
        RustCheckTestCase {
            description: "normal rule options lower the argument budget",
            exception: "[targets.rust.rule_options.FPRSS010]\nmax_arguments = 1\n",
            expected_absent: "Found 0 faults",
            expected_exit_code: 1,
            expected_present: "FPRSS010",
            select: "FPRSS010",
            source: "pub fn sum(left: usize, right: usize) -> usize { left + right }\n",
            source_path: "src/lib.rs",
        },
        RustCheckTestCase {
            description: "normal rule options raise the argument budget",
            exception: "[targets.rust.rule_options.FPRSS010]\nmax_arguments = 2\n",
            expected_absent: "FPRSS010",
            expected_exit_code: 0,
            expected_present: "Found 0 faults",
            select: "FPRSS010",
            source: "pub fn sum(left: usize, right: usize) -> usize { left + right }\n",
            source_path: "src/lib.rs",
        },
        RustCheckTestCase {
            description: "indirectly emitted naming rules reach the public CLI",
            exception: "",
            expected_absent: "Found 0 faults",
            expected_exit_code: 1,
            expected_present: "FPRSN001",
            select: "FPRS",
            source: "pub fn validate_value() -> usize { 1 }\n",
            source_path: "src/lib.rs",
        },
        RustCheckTestCase {
            description: "manifest structure violation uses the public Rust pack identity",
            exception: "",
            expected_absent: "RSL302 crate",
            expected_exit_code: 1,
            expected_present: "FPRSL302  crate does not inherit the workspace lint policy",
            select: "FPRSL302",
            source: "pub fn value() -> usize { 1 }\n",
            source_path: "src/lib.rs",
        },
        RustCheckTestCase {
            description: "malformed Rust is reported by the owned engine path",
            exception: "",
            expected_absent: "FPRSL302",
            expected_exit_code: 1,
            expected_present: "FPRSH902",
            select: "FPRSH902",
            source: "pub fn value( {\n",
            source_path: "src/lib.rs",
        },
        RustCheckTestCase {
            description: "file-level Rust exception suppresses an exact selected diagnostic",
            exception: "[[targets.rust.rule_exceptions]]\nrule = \"FPRSL302\"\npath = \"Cargo.toml\"\nreason = \"Fixture intentionally omits inherited lints.\"\n",
            expected_absent: "FPRSL302",
            expected_exit_code: 0,
            expected_present: "Found 0 faults",
            select: "FPRSL302",
            source: "pub fn value() -> usize { 1 }\n",
            source_path: "src/lib.rs",
        },
        RustCheckTestCase {
            description: "Rust evaluation exclusion suppresses diagnostics owned by that source",
            exception: "[targets.rust.evaluation]\nexclude = [\"src/lib.rs\"]\n",
            expected_absent: "FPRSH902",
            expected_exit_code: 0,
            expected_present: "Found 0 faults",
            select: "FPRSH902",
            source: "pub fn value( {\n",
            source_path: "src/lib.rs",
        },
        RustCheckTestCase {
            description: "Rust modules named build are source rather than web artifacts",
            exception: "",
            expected_absent: "Found 0 faults",
            expected_exit_code: 1,
            expected_present: "src/build/mod.rs",
            select: "FPRSH902",
            source: "pub fn value( {\n",
            source_path: "src/build/mod.rs",
        },
    ];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("Cargo.toml"),
            "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        );
        write(
            repository.path().join("Cargo.lock"),
            "# This file is automatically @generated by Cargo.\n# It is not intended for manual editing.\nversion = 4\n\n[[package]]\nname = \"example\"\nversion = \"0.1.0\"\n",
        );
        write(repository.path().join("src/lib.rs"), "pub mod build;\n");
        write(
            repository.path().join(test_case.source_path),
            test_case.source,
        );
        write(
            repository.path().join("fensu.toml"),
            &format!(
                "[targets.rust]\nanalyzer = \"rust\"\nroots = [\"src\"]\ntests = []\ntooling = []\nrule_packs = [\"rust\"]\nselect = [\"{}\"]\n{}",
                test_case.select, test_case.exception
            ),
        );

        let output = run_check(repository.path());
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_present),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            !stdout.contains(test_case.expected_absent),
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_rust_rule_options_when_checking_then_configuration_fails_closed() {
    let test_cases = [
        InvalidCheckConfigTestCase {
            description: "unrelated native pack options",
            config: "[targets.rust.rule_options.FPDG022]\napproved_loader_boundaries = []\n",
            expected_exit_code: 2,
            expected_error: "not supported by the Rust analyzer",
        },
        InvalidCheckConfigTestCase {
            description: "Rust options on another analyzer",
            config: "[targets.python]\nanalyzer = \"python\"\nroots = [\"src\"]\n[targets.python.rule_options.FPRSS010]\nmax_arguments = 5\n",
            expected_exit_code: 2,
            expected_error: "supported only by the Rust analyzer",
        },
        InvalidCheckConfigTestCase {
            description: "zero argument budget",
            config: "[targets.rust.rule_options.FPRSS010]\nmax_arguments = 0\n",
            expected_exit_code: 2,
            expected_error: "must be a positive integer",
        },
        InvalidCheckConfigTestCase {
            description: "unknown option name",
            config: "[targets.rust.rule_options.FPRSS010]\nmax_args = 5\n",
            expected_exit_code: 2,
            expected_error: "does not declare option max_args",
        },
        InvalidCheckConfigTestCase {
            description: "unknown empty rule table",
            config: "[targets.rust.rule_options.FPRSUNKNOWN]\n",
            expected_exit_code: 2,
            expected_error: "Unknown native rule options code",
        },
        InvalidCheckConfigTestCase {
            description: "invalid parser boundary path",
            config: "[targets.rust.rule_options.FPRSL102]\nrestricted_paths = [\"../outside\"]\n",
            expected_exit_code: 2,
            expected_error: "repository-relative POSIX paths",
        },
    ];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("src/lib.rs"),
            "pub fn value() -> usize { 1 }\n",
        );
        write(
            repository.path().join("Cargo.toml"),
            "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        );
        write(
            repository.path().join("fensu.toml"),
            &format!("{RUST_CONFIG}{}", test_case.config),
        );
        let output = run_check(repository.path());
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stderr}",
            test_case.description
        );
        assert!(
            stderr.contains(test_case.expected_error),
            "{}: {stderr}",
            test_case.description
        );
    }
}

#[test]
fn given_rust_policy_input_when_checking_again_then_cache_invalidates_on_policy_change() {
    let test_cases = [RustCacheTestCase {
        description: "Rust source and project policy share one cache identity",
        expected_cold: "Cache: hits=0 misses=1",
        expected_invalidated: "Cache: hits=0 misses=1",
        expected_warm: "Cache: hits=1 misses=0",
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("Cargo.toml"),
            "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        );
        write(
            repository.path().join("Cargo.lock"),
            "# This file is automatically @generated by Cargo.\n# It is not intended for manual editing.\nversion = 4\n\n[[package]]\nname = \"example\"\nversion = \"0.1.0\"\n",
        );
        write(
            repository.path().join("src/lib.rs"),
            "pub fn value() -> usize { 1 }\n",
        );
        write(repository.path().join("fensu.toml"), RUST_CONFIG);

        let cold = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
        let warm = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
        write(
            repository.path().join("fensu.toml"),
            &format!("{RUST_CONFIG}\n[targets.rust.rule_options.FPRSS010]\nmax_arguments = 5\n"),
        );
        let invalidated = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
        let cold_stderr = String::from_utf8_lossy(&cold.stderr);
        let warm_stderr = String::from_utf8_lossy(&warm.stderr);
        let invalidated_stderr = String::from_utf8_lossy(&invalidated.stderr);

        assert!(
            cold_stderr.contains(test_case.expected_cold),
            "{}: {cold_stderr}",
            test_case.description
        );
        assert!(
            warm_stderr.contains(test_case.expected_warm),
            "{}: {warm_stderr}",
            test_case.description
        );
        assert!(
            invalidated_stderr.contains(test_case.expected_invalidated),
            "{}: {invalidated_stderr}",
            test_case.description
        );
    }
}

#[test]
fn given_unavailable_cargo_metadata_when_checking_then_failure_is_read_only_and_non_cacheable() {
    let test_cases = [RustMetadataCacheTestCase {
        description: "stale lock metadata is neither rewritten nor cached",
        expected_cache: "non_cacheable=1",
        expected_error: "FPRSL302",
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        let stale_lock = "# This file is automatically @generated by Cargo.\n# It is not intended for manual editing.\nversion = 4\n\n[[package]]\nname = \"example\"\nversion = \"0.2.0\"\n";
        write(
            repository.path().join("Cargo.toml"),
            "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        );
        write(repository.path().join("Cargo.lock"), stale_lock);
        write(
            repository.path().join("src/lib.rs"),
            "pub fn value() -> usize { 1 }\n",
        );
        write(repository.path().join("fensu.toml"), RUST_CONFIG);

        for _ in 0..2 {
            let output = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
            let stdout = String::from_utf8_lossy(&output.stdout);
            let stderr = String::from_utf8_lossy(&output.stderr);
            let current_lock = std::fs::read_to_string(repository.path().join("Cargo.lock"))
                .expect("fixture lock remains readable");

            assert!(
                stdout.contains(test_case.expected_error),
                "{}: {stdout}",
                test_case.description
            );
            assert!(
                stderr.contains(test_case.expected_cache),
                "{}: {stderr}",
                test_case.description
            );
            assert_eq!(current_lock, stale_lock, "{}", test_case.description);
        }
    }
}
