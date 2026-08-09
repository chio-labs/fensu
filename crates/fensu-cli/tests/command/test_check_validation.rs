use crate::helpers::{run_check, write};
use crate::test_types::{
    ConfigDiscoveryTestCase, InvalidCheckConfigTestCase, ThresholdPrecedenceTestCase,
};

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
