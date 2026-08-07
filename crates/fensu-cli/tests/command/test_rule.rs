use std::process::Command;

use crate::helpers::write;
use crate::test_types::{RuleColorTestCase, RulePackLookupTestCase, RuleRemediationTestCase};

const CONFIG: &str =
    "roots = [\"src\"]\ntests = [\"tests\"]\ntooling = [\"scripts\"]\nselect = [\"FFA\"]\n";

#[test]
fn given_enabled_native_pack_when_inspecting_alias_then_shows_pack_and_target_without_python() {
    let test_cases = [RulePackLookupTestCase {
        description: "Dagster alias lookup discloses its shipped ownership and canonical target",
        expected_fragments: &[
            "FPDGA001 parameter-annotation",
            "Kind: pack",
            "Pack: dagster",
            "Alias: FFA001",
        ],
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "roots = [\"src\"]\nrule_packs = [\"dagster\"]\nselect = [\"FPDG\"]\n",
        );
        let output = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["rule", "FPDGA001", "--color", "never"])
            .current_dir(repository.path())
            .env(
                "FENSU_PYTHON",
                repository.path().join("python-does-not-exist"),
            )
            .output()
            .expect("native rule process runs");
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(output.status.code(), Some(0), "{}", test_case.description);
        assert!(
            test_case
                .expected_fragments
                .iter()
                .all(|fragment| stdout.contains(fragment)),
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_forced_color_when_inspecting_rule_then_fault_code_renders_in_orange() {
    let test_cases = [RuleColorTestCase {
        description: "rule lookup uses the same bold orange code as fault output",
        expected_fragment: "\x1b[1;38;5;208mFFA001\x1b[0m parameter-annotation",
    }];

    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        let output = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["rule", "FFA001", "--color", "always"])
            .current_dir(repository.path())
            .output()
            .expect("native rule process runs");
        let stdout = String::from_utf8(output.stdout).expect("rule stdout is UTF-8");

        assert_eq!(output.status.code(), Some(0), "{}", test_case.description);
        assert!(
            stdout.contains(test_case.expected_fragment),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_composable_custom_rule_policies_when_inspecting_rules_then_remediations_explain_wrapper() {
    let repository = tempfile::tempdir().expect("temporary repository");
    write(repository.path().join("fensu.toml"), CONFIG);
    let test_cases = [
        RuleRemediationTestCase {
            description: "FFR707 recommends converting wrappers inside the test",
            code: "FFR707",
            expected_fragment: "convert it to RuleCase inside the test",
        },
        RuleRemediationTestCase {
            description: "FFT204 recommends local wrapper dataclasses",
            code: "FFT204",
            expected_fragment: "local wrapper dataclass",
        },
        RuleRemediationTestCase {
            description: "FFT413 recommends constructing framework objects inside tests",
            code: "FFT413",
            expected_fragment: "construct the framework object inside the test",
        },
    ];

    for test_case in &test_cases {
        let output = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["rule", test_case.code, "--color", "never"])
            .current_dir(repository.path())
            .env(
                "FENSU_PYTHON",
                repository.path().join("python-does-not-exist"),
            )
            .output()
            .expect("native rule process runs");

        assert_eq!(output.status.code(), Some(0), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&output.stdout).contains(test_case.expected_fragment),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_fixed_core_constraints_when_inspecting_rules_then_lists_exhaustive_values() {
    let repository = tempfile::tempdir().expect("temporary repository");
    write(repository.path().join("fensu.toml"), CONFIG);
    let test_cases = [
        RuleRemediationTestCase {
            description: "FFR201 discloses its forbidden module filename",
            code: "FFR201",
            expected_fragment: "Forbidden module filenames: misc.py",
        },
        RuleRemediationTestCase {
            description: "FFR204 discloses every forbidden package name",
            code: "FFR204",
            expected_fragment:
                "Forbidden package names: base, common, helpers, lib, misc, shared, util, utils",
        },
        RuleRemediationTestCase {
            description: "FFH002 discloses accepted tooling directive prefixes",
            code: "FFH002",
            expected_fragment: "Allowed standalone comment prefixes: #!, # -*-, # coding:, # noqa, # type:, # pyright:, # pylint:, # pragma:",
        },
        RuleRemediationTestCase {
            description: "FFR301 discloses forbidden role bucket names",
            code: "FFR301",
            expected_fragment: "Forbidden role bucket names: main, _helpers, helpers, classes, models, types, constants, exceptions",
        },
        RuleRemediationTestCase {
            description: "FFR705 discloses allowed tooling roles",
            code: "FFR705",
            expected_fragment: "Allowed tooling role directories: main, _helpers, classes, rules",
        },
        RuleRemediationTestCase {
            description: "FFR401 discloses fixed entry cardinality",
            code: "FFR401",
            expected_fragment: "Required public entry functions: 1",
        },
        RuleRemediationTestCase {
            description: "FFR304 discloses recognized role filenames",
            code: "FFR304",
            expected_fragment: "Recognized runtime role filenames: main.py, helpers.py, classes.py, models.py, types.py, constants.py, exceptions.py",
        },
        RuleRemediationTestCase {
            description: "FFR305 discloses recognized role directories",
            code: "FFR305",
            expected_fragment: "Recognized runtime role directories: main, _helpers, classes, models, types, constants, exceptions",
        },
        RuleRemediationTestCase {
            description: "FFR702 discloses every allowed direct-script call target",
            code: "FFR702",
            expected_fragment: "Allowed direct-script main() call targets: _parse_args, imported main/ entry function",
        },
        RuleRemediationTestCase {
            description: "FFR701 discloses every allowed direct-script function",
            code: "FFR701",
            expected_fragment: "Allowed direct-script command functions: main, _parse_args, _build_parser",
        },
        RuleRemediationTestCase {
            description: "FFR701 discloses every allowed top-level statement kind",
            code: "FFR701",
            expected_fragment: "Allowed direct-script top-level statement kinds: import statement, command function, nonexecuting import guard",
        },
        RuleRemediationTestCase {
            description: "FFR307 discloses recognized top-level role filenames",
            code: "FFR307",
            expected_fragment: "Recognized runtime role filenames: main.py, helpers.py, classes.py, models.py, types.py, constants.py, exceptions.py",
        },
    ];

    for test_case in &test_cases {
        let output = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["rule", test_case.code, "--color", "never"])
            .current_dir(repository.path())
            .output()
            .expect("native rule process runs");

        assert_eq!(output.status.code(), Some(0), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&output.stdout).contains(test_case.expected_fragment),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_configuration_backed_rules_when_inspecting_then_lists_effective_inputs() {
    let repository = tempfile::tempdir().expect("temporary repository");
    write(repository.path().join("fensu.toml"), CONFIG);
    let test_cases = [
        RuleRemediationTestCase {
            description: "FFS001 identifies its effective base threshold",
            code: "FFS001",
            expected_fragment: "max_statements: 40 (base value; role or path overrides may apply)",
        },
        RuleRemediationTestCase {
            description: "FFN001 identifies active no-return naming patterns",
            code: "FFN001",
            expected_fragment: "validate_*: no-return",
        },
        RuleRemediationTestCase {
            description: "FFT001 identifies effective test roots and scopes",
            code: "FFT001",
            expected_fragment: "test_scopes: unit, integration, e2e",
        },
        RuleRemediationTestCase {
            description: "FFL301 identifies effective tooling roots",
            code: "FFL301",
            expected_fragment: "tooling: scripts",
        },
    ];

    for test_case in &test_cases {
        let output = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["rule", test_case.code, "--color", "never"])
            .current_dir(repository.path())
            .output()
            .expect("native rule process runs");

        assert_eq!(output.status.code(), Some(0), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&output.stdout).contains(test_case.expected_fragment),
            "{}",
            test_case.description
        );
    }
}
