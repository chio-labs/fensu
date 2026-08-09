use std::fs;

use crate::helpers::{
    ambiguous_protocol_project, basic_project, method_project, run, run_colored,
    sibling_method_project, text, write, write_bytes,
};
use crate::test_types::{ConfigTargetMappingTestCase, ConfiguredPackageMappingTestCase};

#[test]
fn given_multiple_targets_when_mapping_from_config_then_requires_and_uses_named_selection() {
    let test_cases = [
        ConfigTargetMappingTestCase {
            description: "map selects configured roots from an inline named target",
            arguments: &["second_fn", "--target=second", "--no-cache"],
            expected_exit_code: 0,
            expected_stdout: "frontend/src/second/module.py:1",
            expected_stderr: "",
        },
        ConfigTargetMappingTestCase {
            description: "map rejects ambiguous configured roots",
            arguments: &["second_fn", "--no-cache"],
            expected_exit_code: 2,
            expected_stdout: "",
            expected_stderr: "select one with --target TARGET",
        },
        ConfigTargetMappingTestCase {
            description: "map help documents named target selection",
            arguments: &["--help"],
            expected_exit_code: 0,
            expected_stdout: "--target TARGET",
            expected_stderr: "",
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("multi-target mapping repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.first]\nanalyzer = \"python\"\nroots = [\"src/first\"]\ntests = []\ntooling = []\n[targets.second]\nanalyzer = \"python\"\nroot = \"frontend\"\nroots = [\"src/second\"]\ntests = []\ntooling = []\n",
        );
        write(
            repository.path().join("src/first/module.py"),
            "def first_fn() -> int:\n    return 1\n",
        );
        write(
            repository.path().join("frontend/src/second/module.py"),
            "def second_fn() -> int:\n    return 2\n",
        );

        let output = run(repository.path(), test_case.arguments);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            text(&output.stdout).contains(test_case.expected_stdout),
            "{}",
            test_case.description
        );
        assert!(
            text(&output.stderr).contains(test_case.expected_stderr),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_artifact_named_package_in_configured_root_when_mapping_then_symbols_and_edges_are_complete() {
    let test_cases = [
        ConfiguredPackageMappingTestCase {
            description: "build remains an ordinary configured Python package",
            package_name: "build",
            expected_function_path: "src/pkg/build/worker.py:1",
        },
        ConfiguredPackageMappingTestCase {
            description: "dist remains an ordinary configured Python package",
            package_name: "dist",
            expected_function_path: "src/pkg/dist/worker.py:1",
        },
        ConfiguredPackageMappingTestCase {
            description: "venv remains an ordinary configured Python package",
            package_name: "venv",
            expected_function_path: "src/pkg/venv/worker.py:1",
        },
        ConfiguredPackageMappingTestCase {
            description: "node_modules remains an ordinary configured Python package",
            package_name: "node_modules",
            expected_function_path: "src/pkg/node_modules/worker.py:1",
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("configured package repository");
        write(repository.path().join("fensu.toml"), "roots = [\"src/pkg\"]\n");
        write(repository.path().join("src/pkg/__init__.py"), "");
        write(
            repository
                .path()
                .join(format!("src/pkg/{}/__init__.py", test_case.package_name)),
            "",
        );
        write(
            repository
                .path()
                .join(format!("src/pkg/{}/worker.py", test_case.package_name)),
            "def artifact_worker_fn() -> int:\n    return 1\n",
        );
        write(
            repository.path().join("src/pkg/caller.py"),
            &format!(
                "from pkg.{}.worker import artifact_worker_fn\n\n\ndef caller_fn() -> int:\n    return artifact_worker_fn()\n",
                test_case.package_name
            ),
        );
        for selector in [
            "artifact_worker_fn".to_owned(),
            format!("pkg.{}.worker.artifact_worker_fn", test_case.package_name),
            format!("src/pkg/{}/worker::artifact_worker_fn", test_case.package_name),
        ] {
            let output = run(repository.path(), &[&selector, "--no-cache"]);
            assert_eq!(
                output.status.code(),
                Some(0),
                "{}: {}",
                test_case.description,
                text(&output.stderr)
            );
            assert!(
                text(&output.stdout).contains(test_case.expected_function_path),
                "{}: {selector}",
                test_case.description
            );
        }
        if test_case.package_name == "build" {
            let explicit = run(
                repository.path(),
                &["artifact_worker_fn", "--root", "src/pkg", "--no-cache"],
            );
            assert_eq!(
                explicit.status.code(),
                Some(0),
                "explicit root: {}",
                text(&explicit.stderr)
            );
            assert!(text(&explicit.stdout).contains(test_case.expected_function_path));
        }
        let uncached = run(repository.path(), &["caller_fn", "--no-cache"]);
        let cold = run(repository.path(), &["caller_fn", "--cache-stats"]);
        let warm = run(repository.path(), &["caller_fn", "--cache-stats"]);
        assert_eq!(uncached.status.code(), Some(0), "{}", test_case.description);
        assert!(
            text(&uncached.stdout).contains("artifact_worker_fn(...)"),
            "{}",
            test_case.description
        );
        assert_eq!(uncached.stdout, cold.stdout, "{}", test_case.description);
        assert_eq!(cold.stdout, warm.stdout, "{}", test_case.description);
        assert!(text(&cold.stderr).contains("manifest=miss"));
        assert!(text(&warm.stderr).contains("manifest=hit"));
    }
}

#[test]
fn given_artifact_directory_in_inferred_root_when_mapping_then_generated_code_stays_excluded() {
    let test_cases = [ConfiguredPackageMappingTestCase {
        description: "top-level build output remains excluded without configured roots",
        package_name: "build",
        expected_function_path: "Unknown project function: generated_artifact_fn.",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("inferred artifact repository");
        write(
            repository.path().join("pyproject.toml"),
            "[project]\nname = \"fixture\"\nversion = \"0.0.0\"\n",
        );
        write(
            repository
                .path()
                .join(format!("{}/generated.py", test_case.package_name)),
            "def generated_artifact_fn() -> None:\n    return None\n",
        );
        write(
            repository.path().join("pkg/entry.py"),
            "def included_fn() -> None:\n    return None\n",
        );

        let included = run(repository.path(), &["included_fn", "--no-cache"]);
        let excluded = run(repository.path(), &["generated_artifact_fn", "--no-cache"]);

        assert_eq!(included.status.code(), Some(0), "{}", test_case.description);
        assert_eq!(excluded.status.code(), Some(2), "{}", test_case.description);
        assert!(
            text(&excluded.stderr).contains(test_case.expected_function_path),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_native_map_when_python_is_missing_then_direct_calls_cycles_and_depth_are_deterministic() {
    let repository = tempfile::tempdir().expect("temporary repository");
    basic_project(repository.path());

    let first = run(
        repository.path(),
        &["pkg.entry.run", "--depth", "3", "--no-cache"],
    );
    let second = run(
        repository.path(),
        &["pkg.entry.run", "--depth", "3", "--no-cache"],
    );
    let explicit = run(
        repository.path(),
        &[
            "pkg.entry.run",
            "--direction",
            "downstream",
            "--depth",
            "3",
            "--no-cache",
        ],
    );
    let stdout = text(&first.stdout);

    assert_eq!(first.status.code(), Some(0), "{}", text(&first.stderr));
    assert_eq!(first.stdout, second.stdout);
    assert_eq!(first.stdout, explicit.stdout);
    assert!(stdout.ends_with('\n'));
    assert!(stdout.contains("step(...)  src/pkg/steps.py:3"));
    assert!(stdout.contains("callback(...)  src/pkg/entry.py:5  (unresolved parameter call)"));
    assert!(stdout.contains("run(...)  src/pkg/entry.py:3  (cycle)"));
}

#[test]
fn given_upstream_direction_when_mapping_then_proven_callers_cycles_and_depth_are_deterministic() {
    let repository = tempfile::tempdir().expect("temporary repository");
    basic_project(repository.path());

    let output = run(
        repository.path(),
        &[
            "pkg.steps.step",
            "--direction",
            "upstream",
            "--depth",
            "3",
            "--no-cache",
        ],
    );
    let stdout = text(&output.stdout);

    assert_eq!(output.status.code(), Some(0), "{}", text(&output.stderr));
    assert_eq!(
        stdout,
        "step(...)  src/pkg/steps.py:3\n└── run(...)  src/pkg/entry.py:3\n    └── finish(...)  src/pkg/finish.py:3\n        └── step(...)  src/pkg/steps.py:3  (cycle)\n"
    );
    assert!(!stdout.contains("callback"));

    let limited = run(
        repository.path(),
        &[
            "pkg.steps.step",
            "--direction",
            "upstream",
            "--depth",
            "1",
            "--no-cache",
        ],
    );
    assert!(text(&limited.stdout).contains("run(...)  src/pkg/entry.py:3  (depth limit)"));
}

#[test]
fn given_inherited_method_dispatch_when_mapping_upstream_then_concrete_callers_are_preserved() {
    let repository = tempfile::tempdir().expect("temporary repository");
    method_project(repository.path());

    let output = run(
        repository.path(),
        &[
            "methods.workers.Worker.hook",
            "--direction",
            "upstream",
            "--depth",
            "3",
            "--no-cache",
        ],
    );
    let stdout = text(&output.stdout);

    assert_eq!(output.status.code(), Some(0), "{}", text(&output.stderr));
    assert!(stdout.contains("Worker.hook(...)"));
    assert!(stdout.contains("Worker.run(...)"));
    assert!(stdout.contains("Worker.execute(...)"));
    assert!(stdout.contains("run(...)  src/methods/entry.py:4"));
    assert!(!stdout.contains("dynamic.execute"));
}

#[test]
fn given_sibling_method_dispatch_when_mapping_upstream_then_callers_do_not_cross_subclasses() {
    let repository = tempfile::tempdir().expect("temporary repository");
    sibling_method_project(repository.path());

    let output = run(
        repository.path(),
        &[
            "siblings.workers.ChildA.hook",
            "--direction",
            "upstream",
            "--depth",
            "2",
            "--no-cache",
        ],
    );
    let stdout = text(&output.stdout);

    assert_eq!(output.status.code(), Some(0), "{}", text(&output.stderr));
    assert!(stdout.contains("ChildA.run(...)"));
    assert!(stdout.contains("call_a(...)"));
    assert!(!stdout.contains("ChildB.run(...)"));
    assert!(!stdout.contains("call_b(...)"));
}

#[test]
fn given_unique_protocol_dispatch_when_mapping_upstream_then_proven_protocol_caller_is_included() {
    let repository = tempfile::tempdir().expect("temporary repository");
    method_project(repository.path());

    let output = run(
        repository.path(),
        &[
            "methods.workers.Worker.execute",
            "--direction",
            "upstream",
            "--depth",
            "1",
            "--no-cache",
        ],
    );

    assert_eq!(output.status.code(), Some(0), "{}", text(&output.stderr));
    assert!(text(&output.stdout).contains("run_protocol(...)"));
}

#[test]
fn given_ambiguous_protocol_dispatch_when_mapping_upstream_then_caller_is_not_invented() {
    let repository = tempfile::tempdir().expect("temporary repository");
    ambiguous_protocol_project(repository.path());

    let output = run(
        repository.path(),
        &[
            "protocols.workers.First.execute",
            "--direction",
            "upstream",
            "--depth",
            "2",
            "--no-cache",
        ],
    );

    assert_eq!(output.status.code(), Some(0), "{}", text(&output.stderr));
    assert_eq!(
        text(&output.stdout),
        "First.execute(...)  src/protocols/workers.py:4\n"
    );
}

#[test]
fn given_selector_forms_when_mapping_then_full_partial_path_and_ambiguity_match_contract() {
    let repository = tempfile::tempdir().expect("temporary repository");
    basic_project(repository.path());
    write(
        repository.path().join("src/pkg/classes.py"),
        "class Worker:\n    def execute(self) -> None:\n        return None\n",
    );

    for selector in [
        "pkg.classes.Worker.execute",
        "Worker.execute",
        "src/pkg/classes::Worker.execute",
        "src\\pkg\\classes.py::Worker.execute",
    ] {
        let output = run(repository.path(), &[selector, "--no-cache"]);
        assert_eq!(
            output.status.code(),
            Some(0),
            "{selector}: {}",
            text(&output.stderr)
        );
        assert!(
            text(&output.stdout).contains("Worker.execute(...)"),
            "{selector}"
        );
    }
    let ambiguous = run(repository.path(), &["run", "--no-cache"]);
    let error = text(&ambiguous.stderr);
    assert_eq!(ambiguous.status.code(), Some(2));
    assert!(error.contains("pkg.entry.run, pkg.other.run"));
}

#[test]
fn given_methods_protocols_and_inheritance_when_mapping_then_resolution_stays_conservative() {
    let repository = tempfile::tempdir().expect("temporary repository");
    method_project(repository.path());

    let output = run(
        repository.path(),
        &["methods.entry.run", "--depth", "4", "--no-cache"],
    );
    let stdout = text(&output.stdout);

    assert_eq!(output.status.code(), Some(0), "{}", text(&output.stderr));
    assert!(stdout.contains("Worker.execute(...)"));
    assert!(stdout.contains("Worker.run(...)"));
    assert!(stdout.contains("Worker.hook(...)"));
    assert!(stdout.contains("dynamic.execute(...)"));
    assert!(stdout.contains("(unresolved parameter method)"));
    assert!(!stdout.contains("unresolved protocol dispatch"));

    let cold = run(repository.path(), &["methods.entry.run", "--cache-stats"]);
    let warm = run(repository.path(), &["methods.entry.run", "--cache-stats"]);
    assert!(text(&cold.stderr).contains(
        "manifest=miss parsed_files=3 reused_file_records=0 writes=4"
    ));
    assert!(text(&warm.stderr).contains(
        "manifest=hit parsed_files=0 reused_file_records=0 writes=0"
    ));
    assert_eq!(cold.stdout, warm.stdout);
}

#[test]
fn given_inferred_and_repeated_roots_when_mapping_then_import_ownership_and_order_are_stable() {
    let inferred = tempfile::tempdir().expect("inferred repository");
    write(
        inferred.path().join("pyproject.toml"),
        "[project]\nname = \"demo\"\n",
    );
    write(
        inferred.path().join("src/pkg/entry.py"),
        "def run() -> None:\n    return None\n",
    );
    let inferred_output = run(inferred.path(), &["pkg.entry.run", "--no-cache"]);
    assert_eq!(inferred_output.status.code(), Some(0));
    assert!(text(&inferred_output.stdout).contains("src/pkg/entry.py:1"));

    let repeated = tempfile::tempdir().expect("repeated root repository");
    write(
        repeated.path().join("services/acme/entry.py"),
        "from shared.steps import step\n\ndef run() -> None:\n    step()\n",
    );
    write(
        repeated.path().join("libraries/shared/steps.py"),
        "def step() -> None:\n    return None\n",
    );
    let repeated_output = run(
        repeated.path(),
        &[
            "acme.entry.run",
            "--root",
            "services",
            "--root",
            "libraries",
            "--no-cache",
        ],
    );
    let stdout = text(&repeated_output.stdout);
    assert_eq!(
        repeated_output.status.code(),
        Some(0),
        "{}",
        text(&repeated_output.stderr)
    );
    assert!(stdout.contains("services/acme/entry.py:3"));
    assert!(stdout.contains("libraries/shared/steps.py:1"));
}

#[test]
fn given_path_and_color_modes_when_mapping_then_presentation_matches_cli_contract() {
    let repository = tempfile::tempdir().expect("temporary repository");
    basic_project(repository.path());

    let none = run(
        repository.path(),
        &["pkg.entry.run", "--paths", "none", "--no-cache"],
    );
    assert!(!text(&none.stdout).contains(".py:"));
    let absolute = run(
        repository.path(),
        &["pkg.entry.run", "--paths", "absolute", "--no-cache"],
    );
    assert!(text(&absolute.stdout).contains(&repository.path().to_string_lossy().to_string()));
    let colored = run_colored(
        repository.path(),
        &["pkg.entry.run", "--color", "always", "--no-cache"],
    );
    assert!(colored.stdout.windows(4).any(|window| window == b"\x1b[1;"));
}

#[test]
fn given_supported_encodings_and_invalid_sources_when_mapping_then_decoding_is_actionable() {
    let repository = tempfile::tempdir().expect("temporary repository");
    write(
        repository.path().join("fensu.toml"),
        "roots = [\"src/pkg\"]\n",
    );
    write_bytes(
        repository.path().join("src/pkg/bom.py"),
        b"\xef\xbb\xbfdef run() -> None:\r\n    return None\r\n",
    );
    write_bytes(
        repository.path().join("src/pkg/latin.py"),
        b"# coding: latin-1\ndef cafe() -> str:\n    return 'caf\xe9'\n",
    );
    assert_eq!(
        run(repository.path(), &["run", "--no-cache"]).status.code(),
        Some(0)
    );
    assert_eq!(
        run(repository.path(), &["cafe", "--no-cache"])
            .status
            .code(),
        Some(0)
    );

    write_bytes(
        repository.path().join("src/pkg/latin.py"),
        b"value = '\xff'\n",
    );
    let encoding = run(repository.path(), &["run", "--no-cache"]);
    assert_eq!(encoding.status.code(), Some(2));
    assert!(text(&encoding.stderr).contains("invalid or missing encoding declaration"));
    write(repository.path().join("src/pkg/latin.py"), "def broken(:\n");
    let syntax = run(repository.path(), &["run", "--no-cache"]);
    assert_eq!(syntax.status.code(), Some(2));
    assert!(text(&syntax.stderr).contains("Could not parse"));
}

#[test]
fn given_cache_controls_when_mapping_then_cold_warm_edit_purity_and_failure_are_observable() {
    let repository = tempfile::tempdir().expect("temporary repository");
    basic_project(repository.path());
    let database = repository.path().join(".fensu/cache/v4.db");

    let uncached = run(
        repository.path(),
        &["pkg.entry.run", "--no-cache", "--cache-stats"],
    );
    assert_eq!(uncached.status.code(), Some(0));
    assert!(!database.exists());
    assert!(uncached.stderr.is_empty());

    let cold = run(repository.path(), &["pkg.entry.run", "--cache-stats"]);
    let warm = run(repository.path(), &["pkg.entry.run", "--cache-stats"]);
    assert!(text(&cold.stderr).contains("manifest=miss parsed_files=4"));
    assert!(text(&cold.stderr).contains("reused_file_records=0 writes=5"));
    assert!(text(&warm.stderr).contains("manifest=hit parsed_files=0"));
    assert_eq!(cold.stdout, warm.stdout);
    write(
        repository.path().join("src/pkg/steps.py"),
        "def step() -> None:\n    return None\n",
    );
    let edited = run(repository.path(), &["pkg.entry.run", "--cache-stats"]);
    assert!(text(&edited.stderr)
        .contains("manifest=miss parsed_files=1 reused_file_records=3 writes=2"));
    assert!(!text(&edited.stdout).contains("finish(...)"));

    let failing = tempfile::tempdir().expect("failing cache repository");
    basic_project(failing.path());
    fs::create_dir_all(failing.path().join(".fensu/cache/v4.db")).expect("cache path directory");
    let fallback = run(failing.path(), &["pkg.entry.run", "--cache-stats"]);
    assert_eq!(fallback.status.code(), Some(0));
    assert!(text(&fallback.stderr).contains("publication failed"));
    assert!(text(&fallback.stderr).contains("storage_failed=true"));
}

#[test]
fn given_map_help_and_invalid_arguments_when_parsing_then_argparse_surface_is_preserved() {
    let repository = tempfile::tempdir().expect("temporary repository");
    let help = run(repository.path(), &["--help"]);
    assert_eq!(help.status.code(), Some(0));
    assert!(text(&help.stdout).contains("--cache | --no-cache"));
    assert!(text(&help.stdout).contains("--direction {downstream,upstream}"));
    for arguments in [
        vec![],
        vec!["run", "--depth", "-1"],
        vec!["run", "--direction", "sideways"],
        vec!["run", "--cache", "--no-cache"],
    ] {
        let output = run(repository.path(), &arguments);
        assert_eq!(output.status.code(), Some(2));
        assert!(text(&output.stderr).starts_with("usage: fensu map"));
    }
}

#[test]
fn given_argparse_abbreviations_and_terminator_when_mapping_then_native_surface_matches_oracle() {
    let repository = tempfile::tempdir().expect("temporary repository");
    basic_project(repository.path());

    let abbreviated = run(
        repository.path(),
        &["pkg.entry.run", "--de", "1", "--no-c", "--pa", "none"],
    );
    let abbreviated_stdout = text(&abbreviated.stdout);
    assert_eq!(abbreviated.status.code(), Some(0), "{}", text(&abbreviated.stderr));
    assert!(abbreviated_stdout.contains("step(...)  (depth limit)"));
    assert!(!abbreviated_stdout.contains(".py:"));

    let terminated = run(repository.path(), &["--", "pkg.entry.run"]);
    assert_eq!(terminated.status.code(), Some(0), "{}", text(&terminated.stderr));
    let option_symbol = run(repository.path(), &["--", "--depth"]);
    assert_eq!(option_symbol.status.code(), Some(2));
    assert_eq!(text(&option_symbol.stderr), "Unknown project function: --depth.\n");

    for (abbreviation, expected) in [
        ("--ca", "ambiguous option: --ca could match --cache, --cache-stats"),
        (
            "--c",
            "ambiguous option: --c could match --color, --cache, --cache-stats",
        ),
    ] {
        let output = run(repository.path(), &["pkg.entry.run", abbreviation]);
        assert_eq!(output.status.code(), Some(2));
        assert!(text(&output.stderr).contains(expected));
    }
}

#[test]
fn given_invalid_configured_layout_when_mapping_then_cross_scope_errors_match_oracle() {
    for (config, expected) in [
        (
            "roots = [\"missing\"]\ntests = []\n",
            "Configured root path(s) do not exist: missing.",
        ),
        (
            "roots = [\"../outside\"]\ntests = []\n",
            "Configured path must resolve inside the repository: ../outside",
        ),
        (
            "roots = [\"src/pkg\"]\ntests = [\"src/pkg\"]\n",
            "Configured path cannot belong to both roots and tests:",
        ),
        (
            "roots = [\"src/pkg\"]\ntests = [\"tests/pkg\"]\n",
            "Runtime and test roots must not claim the same import package: pkg",
        ),
        (
            "roots = [\"src/pkg\"]\ntests = []\ntooling = [\"scripts/pkg\"]\n",
            "Runtime and tooling roots must not claim the same import package: pkg",
        ),
    ] {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), config);
        write(
            repository.path().join("src/pkg/entry.py"),
            "def run() -> None:\n    return None\n",
        );

        let output = run(repository.path(), &["run", "--no-cache"]);

        assert_eq!(output.status.code(), Some(2));
        assert!(text(&output.stderr).contains(expected));
    }
}

#[test]
fn given_valid_cross_scope_layout_when_mapping_then_only_runtime_roots_are_indexed() {
    let repository = tempfile::tempdir().expect("temporary repository");
    write(
        repository.path().join("fensu.toml"),
        "roots = [\"src/pkg\"]\ntests = [\"tests\"]\ntooling = [\"scripts/tool\"]\n",
    );
    write(
        repository.path().join("src/pkg/entry.py"),
        "def run() -> None:\n    return None\n",
    );
    write(
        repository.path().join("tests/test_entry.py"),
        "def run() -> None:\n    return None\n",
    );
    write(
        repository.path().join("scripts/tool/task.py"),
        "def run() -> None:\n    return None\n",
    );

    let output = run(repository.path(), &["run", "--no-cache"]);

    assert_eq!(output.status.code(), Some(0), "{}", text(&output.stderr));
    assert!(text(&output.stdout).contains("src/pkg/entry.py:1"));
}

#[test]
fn given_bounded_codec_aliases_when_mapping_then_decoding_is_strict_and_diagnostic() {
    let repository = tempfile::tempdir().expect("temporary repository");
    write(repository.path().join("fensu.toml"), "roots = [\"src/pkg\"]\n");
    write_bytes(
        repository.path().join("src/pkg/entry.py"),
        b"# coding: cp1252\ndef run() -> str:\n    return '\x80'\n",
    );
    let supported = run(repository.path(), &["run", "--no-cache"]);
    assert_eq!(supported.status.code(), Some(0), "{}", text(&supported.stderr));

    write_bytes(
        repository.path().join("src/pkg/entry.py"),
        b"# coding: ascii\ndef run() -> str:\n    return '\xe9'\n",
    );
    let invalid = run(repository.path(), &["run", "--no-cache"]);
    assert_eq!(invalid.status.code(), Some(2));
    assert!(text(&invalid.stderr).contains("source is not valid ASCII"));

    write(
        repository.path().join("src/pkg/entry.py"),
        "# coding: unavailable-codec\ndef run() -> None:\n    return None\n",
    );
    let unsupported = run(repository.path(), &["run", "--no-cache"]);
    assert_eq!(unsupported.status.code(), Some(2));
    assert!(text(&unsupported.stderr).contains(
        "unsupported Python source encoding 'unavailable-codec'; native map supports UTF-8, ASCII, Latin-1, and strict encoding_rs labels"
    ));
}
