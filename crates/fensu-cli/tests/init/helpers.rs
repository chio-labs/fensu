use std::fs;
use std::path::Path;
use std::process::{Command, Output};

fn write(path: impl AsRef<Path>, content: impl AsRef<[u8]>) {
    let path = path.as_ref();
    fs::create_dir_all(path.parent().expect("fixture parent")).expect("fixture directory");
    fs::write(path, content).expect("fixture file");
}

fn run(root: &Path, arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_fensu"))
        .args(arguments)
        .current_dir(root)
        .env("FENSU_PYTHON", root.join("missing-python"))
        .output()
        .expect("native fensu process")
}

fn sveltekit(root: &Path) {
    write(root.join("svelte.config.js"), b"export default {};\n");
    write(
        root.join("package.json"),
        br#"{"devDependencies":{"@sveltejs/kit":"latest"}}"#,
    );
    write(root.join("tsconfig.json"), b"{}\n");
    fs::create_dir_all(root.join("src")).expect("Svelte source root");
}

pub(crate) fn sveltekit_only_repository_writes_explicit_web_target() {
    let repository = tempfile::tempdir().expect("temporary repository");
    sveltekit(repository.path());

    let output = run(repository.path(), &["init", "--yes", "--no-skills"]);
    let config = fs::read_to_string(repository.path().join("fensu.toml")).expect("configuration");

    assert_eq!(
        output.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(
        config,
        "[targets.web]\nanalyzer = \"svelte\"\nroot = \".\"\nroots = [\"src\"]\ntests = []\ntooling = []\ntest_layout = \"mirrored\"\nframework = \"sveltekit\"\nrule_packs = []\nselect = [\"FW\"]\n[targets.web.thresholds]\nmax_entry_statements = 40\nmax_entry_distinct_calls = 20\nmax_entry_locals = 20\nmax_function_statements = 70\n"
    );
    assert!(!repository.path().join("src/web/__init__.py").exists());
    assert_eq!(
        fs::read_to_string(repository.path().join(".gitignore")).expect("Svelte ignore"),
        "# Fensu\n.fensu/cache/\n"
    );
    assert!(String::from_utf8_lossy(&output.stdout).contains(
        "web: analyzer=svelte, root=., roots=src, tests=, tooling=, test_layout=mirrored"
    ));
}

pub(crate) fn generic_node_and_incomplete_svelte_evidence_do_not_detect_target() {
    let repository = tempfile::tempdir().expect("temporary repository");
    write(
        repository.path().join("package.json"),
        br#"{"dependencies":{"@sveltejs/kit":"latest"}}"#,
    );
    write(repository.path().join("tsconfig.json"), b"{}\n");
    fs::create_dir_all(repository.path().join("src")).expect("source root");

    assert_near_miss(repository.path());
}

pub(crate) fn svelte_config_without_kit_dependency_does_not_detect_target() {
    let repository = tempfile::tempdir().expect("temporary repository");
    write(
        repository.path().join("package.json"),
        br#"{"dependencies":{"svelte":"latest"}}"#,
    );
    write(repository.path().join("tsconfig.json"), b"{}\n");
    write(
        repository.path().join("svelte.config.js"),
        b"export default {};\n",
    );
    fs::create_dir_all(repository.path().join("src")).expect("source root");

    assert_near_miss(repository.path());
}

fn assert_near_miss(repository: &Path) {
    let output = run(repository, &["init", "--yes", "--no-skills"]);
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr)
        .contains("Empty repository initialization with --yes requires --name NAME"));
    assert!(!repository.join("fensu.toml").exists());
}

pub(crate) fn mixed_repository_with_colliding_web_names_is_deterministic() {
    let repository = tempfile::tempdir().expect("temporary repository");
    write(repository.path().join("src/api/__init__.py"), b"");
    sveltekit(&repository.path().join("apps/first/web"));
    sveltekit(&repository.path().join("apps/python"));
    sveltekit(&repository.path().join("apps/second/web"));

    let output = run(repository.path(), &["init", "--yes", "--no-skills"]);
    assert_eq!(
        output.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let config = fs::read_to_string(repository.path().join("fensu.toml")).expect("configuration");
    assert!(config.starts_with("[targets.python]\nanalyzer = \"python\""));
    assert!(config.contains("[targets.web]\n"));
    assert!(config.contains("root = \"apps/first/web\""));
    assert!(config.contains("[targets.web-2]\n"));
    assert!(config.contains("root = \"apps/second/web\""));
    assert!(config.contains("[targets.python-2]\n"));
    assert!(config.contains("root = \"apps/python\""));
}

pub(crate) fn detected_target_exclusion_keeps_remaining_targets() {
    let repository = tempfile::tempdir().expect("temporary repository");
    write(repository.path().join("src/api/__init__.py"), b"");
    sveltekit(&repository.path().join("frontend"));

    let output = run(
        repository.path(),
        &[
            "init",
            "--yes",
            "--no-skills",
            "--exclude-target",
            "frontend",
        ],
    );
    let config = fs::read_to_string(repository.path().join("fensu.toml")).expect("configuration");

    assert_eq!(output.status.code(), Some(0));
    assert_eq!(
        config,
        "roots = [\"src/api\"]\ntests = [\"tests\"]\nselect = [\"FF\"]\n"
    );
}

pub(crate) fn empty_sveltekit_preset_runs_without_external_runtime() {
    let repository = tempfile::tempdir().expect("temporary repository");
    let empty_path = repository.path().join("empty-path");
    fs::create_dir(&empty_path).expect("empty executable path");
    let init = run(
        repository.path(),
        &["init", "--yes", "--preset", "sveltekit", "--no-skills"],
    );
    assert_eq!(
        init.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&init.stderr)
    );

    for arguments in [
        vec!["check", "--no-cache", "--no-color"],
        vec!["skills", "--target", "agents"],
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(arguments)
            .current_dir(repository.path())
            .env("PATH", &empty_path)
            .env("FENSU_PYTHON", repository.path().join("missing-python"))
            .output()
            .expect("one native process");
        assert_eq!(
            output.status.code(),
            Some(0),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
    assert!(!repository.path().join("src/__init__.py").exists());
    assert_eq!(
        fs::read_to_string(repository.path().join(".gitignore")).expect("preset ignore"),
        "# Fensu\n.fensu/cache/\n"
    );
}

pub(crate) fn explicit_config_addition_preserves_comments_and_refuses_unsafe_cases() {
    let repository = tempfile::tempdir().expect("temporary repository");
    let original = "# retained\n[targets.api]\nanalyzer = \"python\"\nroots = [\"src/api\"]\n";
    write(repository.path().join("fensu.toml"), original);
    write(repository.path().join("src/api/__init__.py"), b"");
    fs::create_dir_all(repository.path().join("frontend/src")).expect("frontend source");

    let added = run(
        repository.path(),
        &[
            "target",
            "add",
            "web",
            "--preset",
            "sveltekit",
            "--path",
            "frontend",
        ],
    );
    let updated = fs::read_to_string(repository.path().join("fensu.toml")).expect("updated config");
    assert_eq!(
        added.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&added.stderr)
    );
    assert!(updated.starts_with(original));
    assert!(updated.contains("[targets.web]\nanalyzer = \"svelte\""));
    assert!(updated.contains("test_layout = \"mirrored\""));
    assert!(updated.contains("max_entry_statements = 40"));
    assert!(String::from_utf8_lossy(&added.stdout).contains("test_layout=mirrored"));

    let duplicate = run(
        repository.path(),
        &[
            "target",
            "add",
            "web",
            "--preset",
            "sveltekit",
            "--path",
            "frontend",
        ],
    );
    assert_eq!(duplicate.status.code(), Some(2));
    assert_eq!(
        fs::read_to_string(repository.path().join("fensu.toml")).expect("preserved config"),
        updated
    );

    let legacy = tempfile::tempdir().expect("legacy repository");
    write(legacy.path().join("fensu.toml"), b"roots = [\"src/api\"]\n");
    fs::create_dir_all(legacy.path().join("frontend/src")).expect("legacy frontend");
    let refused = run(
        legacy.path(),
        &[
            "target",
            "add",
            "web",
            "--preset",
            "sveltekit",
            "--path",
            "frontend",
        ],
    );
    assert_eq!(refused.status.code(), Some(2));
    assert_eq!(
        fs::read_to_string(legacy.path().join("fensu.toml")).expect("legacy config"),
        "roots = [\"src/api\"]\n"
    );
}

pub(crate) fn python_coverage_package_is_detected() {
    let repository = tempfile::tempdir().expect("coverage repository");
    write(repository.path().join("src/coverage/__init__.py"), b"");

    let output = run(repository.path(), &["init", "--yes", "--no-skills"]);

    assert_eq!(output.status.code(), Some(0));
    assert_eq!(
        fs::read_to_string(repository.path().join("fensu.toml")).expect("coverage config"),
        "roots = [\"src/coverage\"]\ntests = [\"tests\"]\nselect = [\"FF\"]\n"
    );
}

pub(crate) fn invalid_kit_versions_and_demo_trees_stay_excluded() {
    for dependency in ["null", "7", "\"\""] {
        let repository = tempfile::tempdir().expect("conservative repository");
        write(
            repository.path().join("svelte.config.js"),
            b"export default {};\n",
        );
        write(
            repository.path().join("package.json"),
            format!("{{\"devDependencies\":{{\"@sveltejs/kit\":{dependency}}}}}"),
        );
        write(repository.path().join("tsconfig.json"), b"{}\n");
        fs::create_dir_all(repository.path().join("src")).expect("invalid source");
        sveltekit(&repository.path().join("demo"));

        let output = run(repository.path(), &["init", "--yes", "--no-skills"]);

        assert_eq!(output.status.code(), Some(2));
        assert!(String::from_utf8_lossy(&output.stderr)
            .contains("Empty repository initialization with --yes requires --name NAME"));
        assert!(!repository.path().join("fensu.toml").exists());
    }
}

pub(crate) fn explicit_python_example_root_is_available() {
    let repository = tempfile::tempdir().expect("Python example repository");
    write(repository.path().join("examples/pkg/__init__.py"), b"");

    let output = run(
        repository.path(),
        &["init", "--yes", "--no-skills", "--root", "examples/pkg"],
    );

    assert_eq!(output.status.code(), Some(0));
    assert_eq!(
        fs::read_to_string(repository.path().join("fensu.toml")).expect("example config"),
        "roots = [\"examples/pkg\"]\ntests = [\"tests\"]\nselect = [\"FF\"]\n"
    );
}

pub(crate) fn intentional_demo_sveltekit_is_recoverable_with_preset() {
    let repository = tempfile::tempdir().expect("demo checkout");
    let demo = repository.path().join("demo");
    sveltekit(&demo);

    let automatic = run(&demo, &["init", "--yes", "--no-skills"]);
    assert_eq!(automatic.status.code(), Some(2));
    assert!(!demo.join("fensu.toml").exists());

    let preset = run(
        &demo,
        &["init", "--yes", "--preset", "sveltekit", "--no-skills"],
    );
    assert_eq!(preset.status.code(), Some(0));
    assert!(fs::read_to_string(demo.join("fensu.toml"))
        .expect("demo preset config")
        .starts_with("[targets.web]\n"));
}

pub(crate) fn pyproject_target_options_require_manual_edit() {
    let repository = tempfile::tempdir().expect("pyproject repository");
    write(
        repository.path().join("pyproject.toml"),
        b"[tool.fensu.targets.api]\nanalyzer = \"python\"\nroots = [\"src/pkg\"]\n",
    );

    let output = run(
        repository.path(),
        &["init", "--yes", "--preset", "sveltekit"],
    );
    let error = String::from_utf8_lossy(&output.stderr);

    assert_eq!(output.status.code(), Some(2));
    assert!(error.contains("Edit [tool.fensu] in pyproject.toml manually"));
    assert!(error.contains("target add supports fensu.toml only"));
    assert!(!error.contains("use fensu target add for a safe"));
}

#[cfg(unix)]
pub(crate) fn symlinked_paths_never_follow_outside_repository() {
    use std::os::unix::fs::symlink;

    let ignore_repository = tempfile::tempdir().expect("ignore repository");
    let outside = ignore_repository.path().join("outside-ignore");
    write(&outside, b"outside\n");
    symlink(&outside, ignore_repository.path().join(".gitignore")).expect("ignore symlink");
    sveltekit(ignore_repository.path());

    let init = run(ignore_repository.path(), &["init", "--yes", "--no-skills"]);
    assert_eq!(init.status.code(), Some(2));
    assert_eq!(fs::read(&outside).expect("outside ignore"), b"outside\n");
    assert!(!ignore_repository.path().join("fensu.toml").exists());

    let config_repository = tempfile::tempdir().expect("config repository");
    let outside_config = config_repository.path().join("outside-config");
    write(&outside_config, b"roots = [\"src/pkg\"]\n");
    symlink(&outside_config, config_repository.path().join("fensu.toml")).expect("config symlink");
    let config_init = run(
        config_repository.path(),
        &["init", "--yes", "--name", "pkg", "--no-skills"],
    );
    assert_eq!(config_init.status.code(), Some(2));
    assert_eq!(
        fs::read(&outside_config).expect("outside config"),
        b"roots = [\"src/pkg\"]\n"
    );
    fs::create_dir_all(config_repository.path().join("frontend/src"))
        .expect("safe frontend source");
    let config_target = run(
        config_repository.path(),
        &[
            "target",
            "add",
            "web",
            "--preset",
            "sveltekit",
            "--path",
            "frontend",
        ],
    );
    assert_eq!(config_target.status.code(), Some(2));
    assert_eq!(
        fs::read(&outside_config).expect("outside config after target add"),
        b"roots = [\"src/pkg\"]\n"
    );

    fs::remove_file(config_repository.path().join("fensu.toml")).expect("remove config link");
    write(
        config_repository.path().join("fensu.toml"),
        b"[targets.api]\nanalyzer = \"python\"\nroots = [\"src/api\"]\n",
    );
    fs::remove_dir_all(config_repository.path().join("frontend")).expect("remove safe frontend");
    let outside_frontend = tempfile::tempdir().expect("outside frontend");
    fs::create_dir(outside_frontend.path().join("src")).expect("outside source");
    symlink(
        outside_frontend.path(),
        config_repository.path().join("frontend"),
    )
    .expect("target symlink");
    let target = run(
        config_repository.path(),
        &[
            "target",
            "add",
            "web",
            "--preset",
            "sveltekit",
            "--path",
            "frontend",
        ],
    );
    assert_eq!(target.status.code(), Some(2));
    assert!(
        !fs::read_to_string(config_repository.path().join("fensu.toml"))
            .expect("preserved config")
            .contains("targets.web")
    );
    fs::remove_file(config_repository.path().join("frontend")).expect("remove target symlink");
    fs::create_dir_all(config_repository.path().join("frontend/src"))
        .expect("restore frontend source");
    symlink(
        &outside_config,
        config_repository.path().join(".fensu-target-add.lock"),
    )
    .expect("operation lock symlink");
    let locked = run(
        config_repository.path(),
        &[
            "target",
            "add",
            "web",
            "--preset",
            "sveltekit",
            "--path",
            "frontend",
        ],
    );
    assert_eq!(locked.status.code(), Some(2));
    assert_eq!(
        fs::read(&outside_config).expect("outside lock target"),
        b"roots = [\"src/pkg\"]\n"
    );
}

#[cfg(unix)]
pub(crate) fn concurrent_fensu_and_editor_changes_fail_closed() {
    use std::process::Stdio;

    let repository = tempfile::tempdir().expect("racing target repository");
    let original = "[targets.api]\nanalyzer = \"python\"\nroots = [\"src/api\"]\n".to_owned();
    write(repository.path().join("fensu.toml"), &original);
    write(repository.path().join("src/api/__init__.py"), b"");
    fs::create_dir_all(repository.path().join("frontend/src")).expect("frontend source");
    let child = Command::new(env!("CARGO_BIN_EXE_fensu"))
        .args([
            "target",
            "add",
            "web",
            "--preset",
            "sveltekit",
            "--path",
            "frontend",
        ])
        .current_dir(repository.path())
        .env("FENSU_TEST_TARGET_ADD_PAUSE_MS", "1500")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("racing target process");
    let ready = repository.path().join(".fensu-target-add-test-ready");
    std::thread::sleep(std::time::Duration::from_millis(250));
    assert!(ready.is_file(), "deterministic target-add barrier");

    let concurrent_fensu = run(
        repository.path(),
        &[
            "target",
            "add",
            "other",
            "--preset",
            "sveltekit",
            "--path",
            "frontend",
        ],
    );
    assert_eq!(concurrent_fensu.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&concurrent_fensu.stderr)
        .contains("exclusive repository operation lock"));
    write(
        repository.path().join("fensu.toml"),
        format!("{original}# concurrent editor\n"),
    );

    let output = child.wait_with_output().expect("racing result");

    assert_eq!(output.status.code(), Some(2));
    assert!(!fs::read_to_string(repository.path().join("fensu.toml"))
        .expect("concurrent config")
        .contains("targets.web"));
    assert!(!repository.path().join(".fensu-target-add.lock").exists());
    assert!(!ready.exists());
}
