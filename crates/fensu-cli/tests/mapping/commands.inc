use std::fs;

use crate::helpers::{basic_project, method_project, run, run_colored, text, write, write_bytes};

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
    let stdout = text(&first.stdout);

    assert_eq!(first.status.code(), Some(0), "{}", text(&first.stderr));
    assert_eq!(first.stdout, second.stdout);
    assert!(stdout.ends_with('\n'));
    assert!(stdout.contains("step(...)  src/pkg/steps.py:3"));
    assert!(stdout.contains("callback(...)  src/pkg/entry.py:5  (unresolved parameter call)"));
    assert!(stdout.contains("run(...)  src/pkg/entry.py:3  (cycle)"));
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
    for arguments in [
        vec![],
        vec!["run", "--depth", "-1"],
        vec!["run", "--direction", "upstream"],
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
