use crate::helpers::{run_check, write};
use crate::test_types::{
    CanonicalAliasDiagnosticTestCase, ConfigDiscoveryTestCase, InvalidCheckConfigTestCase,
    ProjectAwareTargetTestCase, TargetCacheCheckTestCase, TargetCheckTestCase,
    ThresholdPrecedenceTestCase,
};

#[cfg(unix)]
#[test]
fn given_internal_target_alias_when_checking_then_diagnostic_uses_canonical_prefix_once() {
    use std::os::unix::fs::symlink;

    let test_cases = [CanonicalAliasDiagnosticTestCase {
        description: "Rust diagnostics match canonical target identity instead of alias spelling",
        expected_exit_code: 1,
        expected_present: "canonical/src/pkg/module.py",
        expected_alias_absent: "alias/src/pkg/module.py",
        expected_double_prefix_absent: "canonical/canonical/",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.app]\nanalyzer = \"python\"\nroot = \"alias\"\nroots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA101\"]\n",
        );
        write(
            repository.path().join("canonical/src/pkg/module.py"),
            "VALUE = 1\n",
        );
        symlink(
            repository.path().join("canonical"),
            repository.path().join("alias"),
        )
        .expect("internal target alias");

        let output =
            crate::helpers::run_check_with(repository.path(), &["--target", "app", "--no-cache"]);
        let stdout = String::from_utf8(output.stdout).expect("check stdout is UTF-8");

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(
            stdout.contains(test_case.expected_present),
            "{}",
            test_case.description
        );
        assert!(
            !stdout.contains(test_case.expected_alias_absent),
            "{}",
            test_case.description
        );
        assert!(
            !stdout.contains(test_case.expected_double_prefix_absent),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_non_dot_target_when_project_rule_compares_modules_then_paths_share_target_invariant() {
    let test_cases = [ProjectAwareTargetTestCase {
        description: "external importer clears one FFL105 entry while orphan reports once",
        expected_exit_code: 1,
        expected_present: "frontend/src/pkg/orders/billing/main/orphan.py",
        expected_absent: "frontend/frontend/",
        expected_cleared: "frontend/src/pkg/orders/billing/main/public.py",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.frontend]\nanalyzer = \"python\"\nroot = \"frontend\"\nroots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFL105\"]\n",
        );
        write(
            repository
                .path()
                .join("frontend/src/pkg/orders/billing/main/public.py"),
            "def publish() -> None:\n    pass\n",
        );
        write(
            repository
                .path()
                .join("frontend/src/pkg/orders/billing/main/orphan.py"),
            "def orphan() -> None:\n    pass\n",
        );
        write(
            repository
                .path()
                .join("frontend/src/pkg/inventory/_helpers/use.py"),
            "from pkg.orders.billing.main.public import publish\n",
        );

        let output = crate::helpers::run_check_with(
            repository.path(),
            &["--target", "frontend", "--no-cache"],
        );
        let stdout = String::from_utf8(output.stdout).expect("check stdout is UTF-8");

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
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
        assert!(
            !stdout.contains(test_case.expected_cleared),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_native_policy_when_checking_then_configuration_fails_closed() {
    let test_cases = [
        InvalidCheckConfigTestCase {
            description: "invalid blocking selector cannot select an empty ruleset",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFRR\"]\n",
            expected_exit_code: 2,
            expected_error: "Config key select contains invalid selector FFRR.",
        },
        InvalidCheckConfigTestCase {
            description: "invalid warning selector is rejected",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nwarn = [\"wrong\"]\n",
            expected_exit_code: 2,
            expected_error: "Config key warn contains invalid selector wrong.",
        },
        InvalidCheckConfigTestCase {
            description: "invalid ignore selector is rejected",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nignore = [\"wrong\"]\n",
            expected_exit_code: 2,
            expected_error: "Config key ignore contains invalid selector wrong.",
        },
        InvalidCheckConfigTestCase {
            description: "unmatched blocking selector is rejected",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFX\"]\n",
            expected_exit_code: 2,
            expected_error: "Config key select contains selector FFX, but it matches no rules in the configured catalogue.",
        },
        InvalidCheckConfigTestCase {
            description: "unmatched warning selector is rejected",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = []\nwarn = [\"FFX\"]\n",
            expected_exit_code: 2,
            expected_error: "Config key warn contains selector FFX, but it matches no rules in the configured catalogue.",
        },
        InvalidCheckConfigTestCase {
            description: "unmatched Dagster alias ignore is rejected",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nrule_packs = [\"dagster\"]\nselect = [\"FPDG\"]\nignore = [\"FPDGL101\"]\n",
            expected_exit_code: 2,
            expected_error: "Config key ignore contains selector FPDGL101, but it matches no rules in the configured catalogue.",
        },
        InvalidCheckConfigTestCase {
            description: "unmatched path-scoped ignore selector is rejected",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\n\n[[rule_ignores]]\nrules = [\"FFX\"]\npaths = [\"src/pkg/**\"]\nreason = \"Generated source.\"\n",
            expected_exit_code: 2,
            expected_error: "Config key rule_ignores.rules contains selector FFX, but it matches no rules in the configured catalogue.",
        },
        InvalidCheckConfigTestCase {
            description: "blocking and warning tiers cannot overlap",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\nwarn = [\"FFA001\"]\n",
            expected_exit_code: 2,
            expected_error: "cannot be configured as both blocking and warning",
        },
        InvalidCheckConfigTestCase {
            description: "warning and ignored tiers cannot overlap",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = []\nwarn = [\"FFA001\"]\nignore = [\"FFA001\"]\n",
            expected_exit_code: 2,
            expected_error: "cannot be configured as both warning and ignored",
        },
        InvalidCheckConfigTestCase {
            description: "test scopes reject adjacent separators",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\ntest_scopes = [\"unit_-slow\"]\n",
            expected_exit_code: 2,
            expected_error: "must contain single lowercase path segments",
        },
        InvalidCheckConfigTestCase {
            description: "missing runtime roots cannot produce a clean check",
            config: "roots = [\"missing/pkg\"]\ntests = []\ntooling = []\n",
            expected_exit_code: 2,
            expected_error: "Configured root path(s) do not exist: missing/pkg.",
        },
        InvalidCheckConfigTestCase {
            description: "configured paths cannot escape the repository",
            config: "roots = [\"../outside\"]\ntests = []\ntooling = []\n",
            expected_exit_code: 2,
            expected_error: "Configured path must resolve inside the repository",
        },
        InvalidCheckConfigTestCase {
            description: "one path cannot belong to runtime and test scopes",
            config: "roots = [\"src/pkg\"]\ntests = [\"src/pkg\"]\ntooling = []\n",
            expected_exit_code: 2,
            expected_error: "cannot belong to both roots and tests",
        },
        InvalidCheckConfigTestCase {
            description: "runtime and test roots cannot claim one import package",
            config: "roots = [\"src/pkg\"]\ntests = [\"tests/pkg\"]\ntooling = []\n",
            expected_exit_code: 2,
            expected_error: "Runtime and test roots must not claim the same import package: pkg",
        },
        InvalidCheckConfigTestCase {
            description: "unknown exception codes cannot remain silently dead",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\n\n[[rule_exceptions]]\nrule = \"FFA999\"\npath = \"src/pkg/module.py\"\nreason = \"Unknown.\"\n",
            expected_exit_code: 2,
            expected_error: "Rule exception references unknown rule code: FFA999.",
        },
        InvalidCheckConfigTestCase {
            description: "thresholds above the native metric range are rejected",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\n[thresholds]\nmax_arguments = 4294967296\n",
            expected_exit_code: 2,
            expected_error: "Threshold max_arguments in thresholds is too large.",
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
fn given_specific_and_broad_threshold_overrides_when_checking_then_specific_pattern_wins() {
    let test_cases = [ThresholdPrecedenceTestCase {
        description: "semantic specificity wins over later declaration order",
        expected_exit_code: 0,
        expected_present: "Specific.",
        expected_absent: "Broad.",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFS010\"]\n\n[[threshold_overrides]]\npaths = [\"src/pkg/orders/main/*.py\"]\nthresholds = { max_arguments = 2 }\nreason = \"Specific.\"\n\n[[threshold_overrides]]\npaths = [\"src/pkg/**/main/*.py\"]\nthresholds = { max_arguments = 1 }\nreason = \"Broad.\"\n",
        );
        write(
            repository.path().join("src/pkg/orders/main/entry.py"),
            "def entry(first: int, second: int) -> int:\n    return first + second\n",
        );

        let output = run_check(repository.path());
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout}",
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
fn given_quoted_fensu_table_when_checking_then_pyproject_is_discovered_structurally() {
    let test_cases = [ConfigDiscoveryTestCase {
        description: "quoted TOML table keys identify real Fensu configuration",
        expected_exit_code: 0,
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("quoted pyproject repository");
        write(
            repository.path().join("pyproject.toml"),
            "[tool.\"fensu\"]\nroots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\n",
        );
        write(
            repository.path().join("src/pkg/module.py"),
            "def valid(value: int) -> int:\n    return value\n",
        );

        let output = run_check(repository.path());

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
    }
}

#[test]
fn given_misleading_child_pyproject_when_checking_then_parent_config_is_discovered() {
    let test_cases = [ConfigDiscoveryTestCase {
        description: "comments naming tool.fensu do not shadow a parent config",
        expected_exit_code: 0,
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("parent configuration repository");
        write(
            repository.path().join("fensu.toml"),
            "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\n",
        );
        write(
            repository.path().join("src/pkg/module.py"),
            "def valid(value: int) -> int:\n    return value\n",
        );
        let child = repository.path().join("child");
        write(
            child.join("pyproject.toml"),
            "# [tool.fensu] is documentation, not configuration.\n",
        );

        let output = run_check(&child);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
    }
}

#[test]
fn given_invalid_explicit_targets_when_checking_then_configuration_fails_closed() {
    let test_cases = [
        InvalidCheckConfigTestCase {
            description: "targets must be a table",
            config: "targets = []\n",
            expected_exit_code: 2,
            expected_error: "targets must be a table of named targets",
        },
        InvalidCheckConfigTestCase {
            description: "targets table must not be empty",
            config: "targets = {}\n",
            expected_exit_code: 2,
            expected_error: "must define at least one named target",
        },
        InvalidCheckConfigTestCase {
            description: "named target must be a table",
            config: "targets = { app = \"python\" }\n",
            expected_exit_code: 2,
            expected_error: "target app must be a table",
        },
        InvalidCheckConfigTestCase {
            description: "legacy and explicit configuration cannot be mixed",
            config: "roots = [\"src/pkg\"]\n[targets.app]\nanalyzer = \"python\"\nroots = [\"src/pkg\"]\n",
            expected_exit_code: 2,
            expected_error: "cannot be mixed with legacy top-level config keys: roots",
        },
        InvalidCheckConfigTestCase {
            description: "target analyzer is required",
            config: "[targets.app]\nroots = [\"src/pkg\"]\n",
            expected_exit_code: 2,
            expected_error: "targets.app.analyzer must be a non-empty string",
        },
        InvalidCheckConfigTestCase {
            description: "unknown analyzers fail closed",
            config: "[targets.web]\nanalyzer = \"svelte\"\nroots = [\"src/pkg\"]\n",
            expected_exit_code: 2,
            expected_error: "Unknown analyzer for target web: svelte",
        },
        InvalidCheckConfigTestCase {
            description: "target roots cannot traverse above the repository",
            config: "[targets.app]\nanalyzer = \"python\"\nroot = \"../backend\"\nroots = [\"src/pkg\"]\n",
            expected_exit_code: 2,
            expected_error: "must not escape the repository",
        },
        InvalidCheckConfigTestCase {
            description: "backslash target roots cannot traverse above the repository",
            config: "[targets.app]\nanalyzer = \"python\"\nroot = 'frontend\\..\\..\\backend'\nroots = [\"src/pkg\"]\n",
            expected_exit_code: 2,
            expected_error: "must not escape the repository",
        },
        InvalidCheckConfigTestCase {
            description: "target roots cannot be absolute",
            config: "[targets.app]\nanalyzer = \"python\"\nroot = \"/backend\"\nroots = [\"src/pkg\"]\n",
            expected_exit_code: 2,
            expected_error: "must be repository-relative",
        },
        InvalidCheckConfigTestCase {
            description: "multiple targets require explicit selection",
            config: "[targets.api]\nanalyzer = \"python\"\nroots = [\"src/pkg\"]\n[targets.worker]\nanalyzer = \"python\"\nroots = [\"src/pkg\"]\n",
            expected_exit_code: 2,
            expected_error: "select one with --target TARGET",
        },
        InvalidCheckConfigTestCase {
            description: "unselected targets must define non-empty roots",
            config: "[targets.valid]\nanalyzer = \"python\"\nroots = [\"src/pkg\"]\n[targets.invalid]\nanalyzer = \"python\"\nroots = []\n",
            expected_exit_code: 2,
            expected_error: "Config must define at least one root in roots.",
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
fn given_explicit_python_targets_when_checking_then_selects_requested_target() {
    let test_cases = [
        TargetCheckTestCase {
            description: "inline clean named target passes",
            arguments: &["--target=clean"],
            expected_exit_code: 0,
            expected_stdout: "Found 0 faults",
            expected_stderr: "",
        },
        TargetCheckTestCase {
            description: "faulty named target reports only its repository path",
            arguments: &["--target", "faulty"],
            expected_exit_code: 1,
            expected_stdout: "frontend/src/faulty/module.py",
            expected_stderr: "",
        },
        TargetCheckTestCase {
            description: "unknown named target fails closed",
            arguments: &["--target", "missing"],
            expected_exit_code: 2,
            expected_stdout: "",
            expected_stderr: "Unknown target name: missing",
        },
        TargetCheckTestCase {
            description: "inline long-help target value is not treated as help",
            arguments: &["--target=--help"],
            expected_exit_code: 0,
            expected_stdout: "Found 0 faults",
            expected_stderr: "",
        },
        TargetCheckTestCase {
            description: "inline short-help target value is not treated as help",
            arguments: &["--target=-h"],
            expected_exit_code: 0,
            expected_stdout: "Found 0 faults",
            expected_stderr: "",
        },
        TargetCheckTestCase {
            description: "backslash traversal target normalizes to backend",
            arguments: &["--target", "backend"],
            expected_exit_code: 1,
            expected_stdout: "backend/src/pkg/module.py",
            expected_stderr: "",
        },
        TargetCheckTestCase {
            description: "separated long-help token is rejected as a missing target argument",
            arguments: &["--target", "--help"],
            expected_exit_code: 2,
            expected_stdout: "",
            expected_stderr: "argument --target: expected one argument",
        },
        TargetCheckTestCase {
            description: "separated short-help token is rejected as a missing target argument",
            arguments: &["--target", "-h"],
            expected_exit_code: 2,
            expected_stdout: "",
            expected_stderr: "argument --target: expected one argument",
        },
    ];
    let repository = tempfile::tempdir().expect("temporary repository");
    write(
        repository.path().join("fensu.toml"),
        "[targets.clean]\nanalyzer = \"python\"\nroots = [\"src/clean\"]\ntests = []\ntooling = []\nselect = [\"FFA101\"]\n[targets.faulty]\nanalyzer = \"python\"\nroot = \"./frontend/nested/..\"\nroots = [\"src/faulty\"]\ntests = []\ntooling = []\nselect = [\"FFA101\"]\n[targets.backend]\nanalyzer = \"python\"\nroot = 'frontend\\..\\backend'\nroots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA101\"]\n[targets.\"--help\"]\nanalyzer = \"python\"\nroots = [\"src/clean\"]\ntests = []\ntooling = []\nselect = [\"FFA101\"]\n[targets.\"-h\"]\nanalyzer = \"python\"\nroots = [\"src/clean\"]\ntests = []\ntooling = []\nselect = [\"FFA101\"]\n",
    );
    write(
        repository.path().join("src/clean/module.py"),
        "VALUE: int = 1\n",
    );
    write(
        repository.path().join("frontend/src/faulty/module.py"),
        "VALUE = 1\n",
    );
    write(
        repository.path().join("backend/src/pkg/module.py"),
        "VALUE = 1\n",
    );

    for test_case in &test_cases {
        let output = crate::helpers::run_check_with(repository.path(), test_case.arguments);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&output.stdout).contains(test_case.expected_stdout),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_stderr),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_unselected_target_when_checking_selected_target_then_configuration_fails_closed() {
    let test_cases = [TargetCheckTestCase {
        description: "selected valid target cannot hide invalid unselected roots",
        arguments: &["--target", "valid"],
        expected_exit_code: 2,
        expected_stdout: "",
        expected_stderr: "Config must define at least one root in roots.",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.valid]\nanalyzer = \"python\"\nroots = [\"src/pkg\"]\n[targets.invalid]\nanalyzer = \"python\"\nroots = []\n",
        );
        write(
            repository.path().join("src/pkg/module.py"),
            "VALUE: int = 1\n",
        );

        let output = crate::helpers::run_check_with(repository.path(), test_case.arguments);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&output.stdout).contains(test_case.expected_stdout),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_stderr),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_one_explicit_python_target_when_checking_then_selects_it_automatically() {
    let test_cases = [TargetCheckTestCase {
        description: "one explicit target needs no target argument",
        arguments: &[],
        expected_exit_code: 0,
        expected_stdout: "Found 0 faults",
        expected_stderr: "",
    }];
    let repository = tempfile::tempdir().expect("temporary repository");
    write(
        repository.path().join("fensu.toml"),
        "[targets.app]\nanalyzer = \"python\"\nroots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA101\"]\n",
    );
    write(
        repository.path().join("src/pkg/module.py"),
        "VALUE: int = 1\n",
    );

    for test_case in &test_cases {
        let output = crate::helpers::run_check_with(repository.path(), test_case.arguments);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&output.stdout).contains(test_case.expected_stdout),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_stderr),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_target_local_pyproject_when_checking_then_entrypoints_use_target_metadata() {
    let test_cases = [TargetCheckTestCase {
        description: "frontend pyproject entrypoint justifies its public main entry",
        arguments: &["--target", "frontend", "--no-cache"],
        expected_exit_code: 0,
        expected_stdout: "Found 0 faults",
        expected_stderr: "",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.frontend]\nanalyzer = \"python\"\nroot = \"frontend\"\nroots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFL105\"]\n",
        );
        write(
            repository.path().join("pyproject.toml"),
            "[project]\nname = \"repository-decoy\"\nversion = \"0.0.0\"\n",
        );
        write(
            repository.path().join("frontend/pyproject.toml"),
            "[project]\nname = \"frontend\"\nversion = \"0.0.0\"\n[project.scripts]\nrun = \"pkg.orders.main.run:run\"\n",
        );
        write(
            repository
                .path()
                .join("frontend/src/pkg/orders/main/run.py"),
            "def run() -> None:\n    pass\n",
        );

        let output = crate::helpers::run_check_with(repository.path(), test_case.arguments);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(
            String::from_utf8_lossy(&output.stdout).contains(test_case.expected_stdout),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_stderr),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_alternating_cached_targets_when_checking_then_output_is_not_replayed() {
    let test_cases = [TargetCacheCheckTestCase {
        description: "alternating target roots cannot replay another target's output",
        expected_lenient_exit_code: 0,
        expected_strict_exit_code: 1,
        expected_strict_stdout: "FFA101",
        expected_lenient_absent: "FFA101",
    }];
    let repository = tempfile::tempdir().expect("temporary repository");
    write(
        repository.path().join("fensu.toml"),
        "[targets.lenient]\nanalyzer = \"python\"\nroot = \"frontend-a\"\nroots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA101\"]\n[targets.strict]\nanalyzer = \"python\"\nroot = \"frontend-b\"\nroots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA101\"]\n",
    );
    write(
        repository.path().join("frontend-a/src/pkg/module.py"),
        "VALUE: int = 1\n",
    );
    write(
        repository.path().join("frontend-b/src/pkg/module.py"),
        "VALUE = 1\n",
    );

    for test_case in &test_cases {
        let lenient =
            crate::helpers::run_check_with(repository.path(), &["--cache", "--target", "lenient"]);
        let strict =
            crate::helpers::run_check_with(repository.path(), &["--cache", "--target", "strict"]);
        let lenient_again =
            crate::helpers::run_check_with(repository.path(), &["--cache", "--target", "lenient"]);

        assert_eq!(
            lenient.status.code(),
            Some(test_case.expected_lenient_exit_code),
            "{}",
            test_case.description
        );
        assert_eq!(
            strict.status.code(),
            Some(test_case.expected_strict_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&strict.stdout).contains(test_case.expected_strict_stdout),
            "{}",
            test_case.description
        );
        assert_eq!(
            lenient_again.status.code(),
            Some(test_case.expected_lenient_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            !String::from_utf8_lossy(&lenient_again.stdout)
                .contains(test_case.expected_lenient_absent),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_check_help_when_rendering_then_documents_target_option() {
    let test_cases = [TargetCheckTestCase {
        description: "check help bypasses ambiguous config and documents target",
        arguments: &["--help"],
        expected_exit_code: 0,
        expected_stdout: "--target TARGET",
        expected_stderr: "",
    }];
    let repository = tempfile::tempdir().expect("temporary repository");
    write(
        repository.path().join("fensu.toml"),
        "[targets.api]\nanalyzer = \"python\"\nroots = [\"src/api\"]\n[targets.worker]\nanalyzer = \"python\"\nroots = [\"src/worker\"]\n",
    );

    for test_case in &test_cases {
        let output = crate::helpers::run_check_with(repository.path(), test_case.arguments);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&output.stdout).contains(test_case.expected_stdout),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_stderr),
            "{}",
            test_case.description
        );
    }
}
