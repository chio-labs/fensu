use crate::helpers::{run_check, run_check_with, write};
use crate::test_types::{CheckPolicyTestCase, InvalidCheckConfigTestCase, SymbolExceptionTestCase};

#[test]
fn given_target_local_exception_when_checking_then_path_resolves_from_target_root() {
    let test_cases = [CheckPolicyTestCase {
        description: "target-local exception suppresses a repository-visible frontend fault",
        expected_exit_code: 0,
        expected_present: "Applied 1 rule exception",
        expected_absent: "frontend/src/pkg/bad.py:1",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.frontend]\nanalyzer = \"python\"\nroot = \"frontend\"\nroots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\n\n[[targets.frontend.rule_exceptions]]\nrule = \"FFA001\"\npath = \"src/pkg/bad.py\"\nreason = \"Accepted target-local callback.\"\n",
        );
        write(
            repository.path().join("frontend/src/pkg/bad.py"),
            "def bad(value):\n    return value\n",
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
fn given_warning_and_exact_exception_when_rule_ignore_overlaps_then_policy_order_is_preserved() {
    let test_cases = [CheckPolicyTestCase {
        description: "exact exceptions remain visible before overlapping ignores filter findings",
        expected_exit_code: 0,
        expected_present: "Applied 1 rule exception",
        expected_absent: "src/pkg/generated/bad.py:1",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = []\nwarn = [\"FFA001\"]\n\n[[rule_exceptions]]\nrule = \"FFA001\"\npath = \"src/pkg/generated/bad.py\"\nreason = \"Exact accepted adapter.\"\n\n[[rule_ignores]]\nrules = [\"FFA001\"]\npaths = [\"src/pkg/generated/**\"]\nreason = \"Generated interfaces are checked upstream.\"\n",
        );
        write(
            repository.path().join("src/pkg/generated/bad.py"),
            "def generated(value):\n    return value\n",
        );

        let output = run_check_with(repository.path(), &["--warn", "--no-cache"]);
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
fn given_symbol_scoped_rule_exception_when_checking_natively_then_only_named_owner_is_suppressed() {
    let test_cases = [SymbolExceptionTestCase {
        description: "symbol scope suppresses the named owner and retains its file siblings",
        source: "def callback(value: int) -> None:\n    return None\n\n\ndef retained(value: int) -> None:\n    return None\n",
        expected_exit_code: 1,
        expected_applied: "Applied 1 rule exception",
        expected_retained_location: "src/pkg/external.py:5:",
        expected_suppressed_location: "src/pkg/external.py:1:",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFS120\"]\n\n[thresholds]\nmax_positional_args = 0\n\n[[rule_exceptions]]\nrule = \"FFS120\"\npath = \"src/pkg/external.py\"\nsymbols = [\"callback\"]\nreason = \"The external API invokes this callback positionally.\"\n",
        );
        write(
            repository.path().join("src/pkg/external.py"),
            test_case.source,
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
            stdout.contains(test_case.expected_applied),
            "{}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_retained_location),
            "{}",
            test_case.description
        );
        assert!(
            !stdout.contains(test_case.expected_suppressed_location),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_target_local_symbol_exception_when_checking_then_owner_is_found_without_staleness() {
    let test_cases = [SymbolExceptionTestCase {
        description: "non-dot target resolves symbol owner against target-relative source key",
        source: "def callback(value: int) -> None:\n    return None\n\n\ndef retained(value: int) -> None:\n    return None\n",
        expected_exit_code: 1,
        expected_applied: "Applied 1 rule exception",
        expected_retained_location: "frontend/src/pkg/external.py:5:",
        expected_suppressed_location: "frontend/src/pkg/external.py:1:",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.frontend]\nanalyzer = \"python\"\nroot = \"frontend\"\nroots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFS120\"]\n\n[targets.frontend.thresholds]\nmax_positional_args = 0\n\n[[targets.frontend.rule_exceptions]]\nrule = \"FFS120\"\npath = \"src/pkg/external.py\"\nsymbols = [\"callback\"]\nreason = \"External callback remains positional.\"\n",
        );
        write(
            repository.path().join("frontend/src/pkg/external.py"),
            test_case.source,
        );

        let output = run_check(repository.path());
        let stdout = String::from_utf8(output.stdout).expect("check stdout is UTF-8");

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(
            stdout.contains(test_case.expected_applied),
            "{}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_retained_location),
            "{}",
            test_case.description
        );
        assert!(
            !stdout.contains(test_case.expected_suppressed_location),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_suffix_matching_exception_path_when_checking_then_only_exact_paths_suppress() {
    let test_cases = [InvalidCheckConfigTestCase {
        description: "an exception path that merely suffix-matches suppresses nothing",
        config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\n\n[[rule_exceptions]]\nrule = \"FFA001\"\npath = \"nested/a.py\"\nreason = \"Exactly one repository-relative target.\"\n",
        expected_exit_code: 2,
        expected_error: "Rule exception no longer matches a fault: FFA001 nested/a.py",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
        write(repository.path().join("nested/a.py"), "value: int = 1\n");
        write(
            repository.path().join("src/pkg/nested/a.py"),
            "def bad(value):\n    return value\n",
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
fn given_exception_for_unevaluated_rule_when_checking_without_warnings_then_it_is_not_stale() {
    let test_cases = [CheckPolicyTestCase {
        description: "a warn-only exception is ignored when warnings are not evaluated",
        expected_exit_code: 0,
        expected_present: "Found 0 faults",
        expected_absent: "no longer matches a fault",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = []\nwarn = [\"FFA001\"]\n\n[[rule_exceptions]]\nrule = \"FFA001\"\npath = \"src/pkg/bad.py\"\nreason = \"Accepted while warnings stay advisory.\"\n",
        );
        write(
            repository.path().join("src/pkg/bad.py"),
            "def bad(value):\n    return value\n",
        );

        let output = run_check(repository.path());
        let combined = format!(
            "{}{}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        );

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            combined.contains(test_case.expected_present),
            "{}",
            test_case.description
        );
        assert!(
            !combined.contains(test_case.expected_absent),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_unselected_target_with_stale_exception_when_checking_one_target_then_it_is_ignored() {
    let test_cases = [CheckPolicyTestCase {
        description: "unselected exception is ignored but all-target validation reports staleness",
        expected_exit_code: 2,
        expected_present: "no longer matches a fault",
        expected_absent: "no longer matches",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.selected]\nanalyzer = \"python\"\nroots = [\"src/selected\"]\ntests = []\ntooling = []\nselect = [\"FFA101\"]\n[targets.stale]\nanalyzer = \"python\"\nroots = [\"src/stale\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\n[[targets.stale.rule_exceptions]]\nrule = \"FFA001\"\npath = \"src/stale/module.py\"\nreason = \"No longer faults.\"\n",
        );
        write(
            repository.path().join("src/selected/module.py"),
            "VALUE: int = 1\n",
        );
        write(
            repository.path().join("src/stale/module.py"),
            "def valid(value: int) -> int:\n    return value\n",
        );

        let selected = run_check_with(repository.path(), &["--target", "selected"]);
        let all = run_check(repository.path());

        assert_eq!(selected.status.code(), Some(0), "{}", test_case.description);
        assert!(
            !String::from_utf8_lossy(&selected.stderr).contains(test_case.expected_absent),
            "{}",
            test_case.description
        );
        assert_eq!(
            all.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&all.stderr).contains(test_case.expected_present),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_unresolvable_exception_targets_when_checking_then_configuration_fails_loudly() {
    let test_cases = [
        InvalidCheckConfigTestCase {
            description: "an exception path that does not exist is rejected",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\n\n[[rule_exceptions]]\nrule = \"FFA001\"\npath = \"src/pkg/missing.py\"\nreason = \"Points at a file that is absent.\"\n",
            expected_exit_code: 2,
            expected_error: "Rule exception path does not exist: src/pkg/missing.py.",
        },
        InvalidCheckConfigTestCase {
            description: "an exception symbol that does not exist is rejected",
            config: "roots = [\"src/pkg\"]\ntests = []\ntooling = []\nselect = [\"FFA001\"]\n\n[[rule_exceptions]]\nrule = \"FFA001\"\npath = \"src/pkg/external.py\"\nsymbols = [\"absent\"]\nreason = \"Names a function that was renamed.\"\n",
            expected_exit_code: 2,
            expected_error: "Rule exception symbol does not exist in src/pkg/external.py: absent.",
        },
    ];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
        write(
            repository.path().join("src/pkg/external.py"),
            "def callback(value):\n    return value\n",
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
